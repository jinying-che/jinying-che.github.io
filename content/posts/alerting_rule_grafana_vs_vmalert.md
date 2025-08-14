---
title: "alerting rule: grafana vs vmalert"
date: "2024-11-24T16:19:22+08:00"
tags: ["grafana", "vmalert"]
description: "how alerting rule is implemented in grafana and vmalert"
---

Let's try to understand how alerting rule is implemented in two open source projects: **grafana** and **vmalert**.

# Version
use the latest version of the according source code:
- grafana [v11.3.1](https://github.com/grafana/grafana/tree/v11.3.1)
- vmalert [v1.106.1](https://github.com/VictoriaMetrics/VictoriaMetrics/tree/v1.106.1)

# Flow
### grafana
![grafana alert](/images/grafana_alert.png)
- Scheduler -> fetch alerting rules -> start *goroutine* for each alerting rule 
  - `pkg/services/ngalert/schedule/schedule.go:280`
- Scheduler -> send evaluation event(when internal elapsed) -> goroutine -> evaluation 
  - `pkg/services/ngalert/schedule/alert_rule.go:242`
- Schedduler -> stop the goroutine (alerting rule delted) according to the heartbeat
  - `pkg/services/ngalert/schedule/alert_rule.go:355`

### vmalert
![vmalert](/images/vmalert.png)
- configReload (cron job by configCheckInterval) -> loading alerting rule files -> `[]config.Group`
- `[]config.Group` -> diff -> manager -> **start** the new `rule.Group` and **delete** the old `rule.Group`
- start `rule.Group` per *goroutine* -> executor -> execConcurrently (`[]rule.Rule`) -> rule.exec() per *goroutine*

# Evaluation 
### grafana
> code entrance: `pkg/services/ngalert/schedule/alert_rule.go:327`

evalCh -> event -> alertRule -> evaluate:  
  - eval.EvaluatorFactory -> create -> ConditionEvaluator (`BuildPipeline -> buildDependencyGraph -> buildExecutionOrder -> []Node`)
  - ConditionEvaluator -> Evaluate
    - expressionExecutor -> ExecutePipeline (DataPipeline []Node)
      - DataPipeline -> excute -> for loop []Node -> backend.QueryDataResponse
    - backend.QueryDataResponse -> EvaluateAlert -> Results
  - Results -> stateManager.ProcessEvalResults

### vmalert
> code entrance: `app/vmalert/rule/group.go:311`

rule.Group -> exec(rule.Rule) concurrently:
  - executor instant query (for now) -> response (label set of Metric that needs alerting)
    - response -> update AlertingRule.alerts 
  - alerts -> executor.Notifier

```go
// Querier interface wraps Query and QueryRange methods
type Querier interface {
	// Query is used for the rule evaluation
	Query(ctx context.Context, query string, ts time.Time) (Result, *http.Request, error)
    // QueryRange is used for rule replay 
	QueryRange(ctx context.Context, query string, from, to time.Time) (Result, error)
}
```

# Data Structure
### grafana
alert rule
```go
// pkg/services/ngalert/models/alert_rule.go:247

// AlertRule is the model for alert rules in unified alerting.
type AlertRule struct {
	ID              int64
	OrgID           int64
	Title           string
	Condition       string
	Data            []AlertQuery
	Updated         time.Time
	IntervalSeconds int64
	Version         int64
	UID             string
	NamespaceUID    string
	DashboardUID    *string
	PanelID         *int64
	RuleGroup       string
	RuleGroupIndex  int
	Record          *Record
	NoDataState     NoDataState
	ExecErrState    ExecutionErrorState
	// ideally this field should have been apimodels.ApiDuration
	// but this is currently not possible because of circular dependencies
	For                  time.Duration
	Annotations          map[string]string
	Labels               map[string]string
	IsPaused             bool
	NotificationSettings []NotificationSettings
	Metadata             AlertRuleMetadata
}

// AlertQuery represents a single query associated with an alert definition.
type AlertQuery struct {
	// RefID is the unique identifier of the query, set by the frontend call.
	RefID string `json:"refId"`

	// QueryType is an optional identifier for the type of query.
	// It can be used to distinguish different types of queries.
	QueryType string `json:"queryType"`

	// RelativeTimeRange is the relative Start and End of the query as sent by the frontend.
	RelativeTimeRange RelativeTimeRange `json:"relativeTimeRange"`

	// Grafana data source unique identifier; it should be '__expr__' for a Server Side Expression operation.
	DatasourceUID string `json:"datasourceUid"`

	// JSON is the raw JSON query and includes the above properties as well as custom properties.
	Model json.RawMessage `json:"model"`

	modelProps map[string]any
}
```
Node
```go
// pkg/expr/graph.go
const (
	// TypeCMDNode is a NodeType for expression commands.
	TypeCMDNode NodeType = iota
	// TypeDatasourceNode is a NodeType for datasource queries.
	TypeDatasourceNode
	// TypeMLNode is a NodeType for Machine Learning queries.
	TypeMLNode
)

// pkg/expr/nodes.go
const (
	// TypeUnknown is the CMDType for an unrecognized expression type.
	TypeUnknown CommandType = iota
	// TypeMath is the CMDType for a math expression.
	TypeMath
	// TypeReduce is the CMDType for a reduction expression.
	TypeReduce
	// TypeResample is the CMDType for a resampling expression.
	TypeResample
	// TypeClassicConditions is the CMDType for the classic condition operation.
	TypeClassicConditions
	// TypeThreshold is the CMDType for checking if a threshold has been crossed
	TypeThreshold
	// TypeSQL is the CMDType for running SQL expressions
	TypeSQL
)
```
### vmalert
```go
// app/vmalert/rule/alerting.go:24
// AlertingRule is basic alert entity
type AlertingRule struct {
	Type          config.Type
	RuleID        uint64
	Name          string
	Expr          string
	For           time.Duration
	KeepFiringFor time.Duration
	Labels        map[string]string
	Annotations   map[string]string
	GroupID       uint64
	GroupName     string
	File          string
	EvalInterval  time.Duration
	Debug         bool

	q datasource.Querier

	alertsMu sync.RWMutex
	// stores list of active alerts
	alerts map[uint64]*notifier.Alert

	// state stores recent state changes
	// during evaluations
	state *ruleState

	metrics *alertingRuleMetrics
}

// app/vmalert/rule/group.go:40
// Group is an entity for grouping rules
type Group struct {
	mu         sync.RWMutex
	Name       string
	File       string
	Rules      []Rule
	Type       config.Type
	Interval   time.Duration
	EvalOffset *time.Duration
	// EvalDelay will adjust timestamp for rule evaluation requests to compensate intentional query delay from datasource.
	// see https://github.com/VictoriaMetrics/VictoriaMetrics/issues/5155
	EvalDelay      *time.Duration
	Limit          int
	Concurrency    int
	Checksum       string
	LastEvaluation time.Time

	Labels          map[string]string
	Params          url.Values
	Headers         map[string]string
	NotifierHeaders map[string]string

	doneCh     chan struct{}
	finishedCh chan struct{}
	// channel accepts new Group obj
	// which supposed to update current group
	updateCh chan *Group
	// evalCancel stores the cancel fn for interrupting
	// rules evaluation. Used on groups update() and close().
	evalCancel context.CancelFunc

	metrics *groupMetrics
	// evalAlignment will make the timestamp of group query
	// requests be aligned with interval
	evalAlignment *bool
}
```
