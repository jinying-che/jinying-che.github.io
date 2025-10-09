---
title: "How grafana works with prometheus"
date: "2025-10-08T15:11:02+08:00"
tags: ["grafana", "prometheus"]
description: "Dive into how Grafana integrates with Prometheus for data visualization and monitoring"
draft: false
---

## Plugin Structure

```
grafana/
├── pkg/                                    # Backend (Go)
│   ├── tsdb/prometheus/                   # Prometheus service wrapper
│   │   └── prometheus.go                  # Service implementation
│   └── promlib/                           # Core Prometheus library
│       ├── library.go                     # Main service entry point
│       ├── client/                        # HTTP client for Prometheus API
│       │   └── client.go                  # QueryRange, QueryInstant, QueryExemplars
│       ├── converter/                     # Response parsing
│       │   └── prom.go                    # JSON to DataFrame conversion
│       ├── querydata/                     # Query execution
│       │   ├── request.go                 # Query processing and execution
│       │   └── response.go                # Response parsing and metadata
│       └── models/                        # Data models
│           └── query.go                   # Query model and variable interpolation
│
└── packages/grafana-prometheus/           # Frontend (TypeScript)
    └── src/
        ├── datasource.ts                  # Main datasource class
        ├── result_transformer.ts          # DataFrame transformation for visualization
        ├── querybuilder/                  # Query builder UI
        └── components/                    # UI components
```

## Architecture Flow

```
┌────────────────────────────────────────────────────────────────
│                          Grafana Frontend                      
│  ┌─────────────────────────────────────────────────────────────
│  │  [REQUEST ↓] Explore / Dashboard                            
│  │  └─> PrometheusDatasource.query()                           
│  │      ├─> getDefaultQuery() - Get default query for app      
│  │      ├─> applyTemplateVariables() - Apply variables         
│  │      ├─> processTargetV2() - Split instant+range queries    
│  │      └─> DataSourceWithBackend.query() (SDK)                
│  └─────────────────────────────────────────────────────────────
│                              ↓ HTTP POST /api/ds/query         
│                              ↑ DataQueryResponse               
│  ┌─────────────────────────────────────────────────────────────
│  │  [RESPONSE ↑] Frontend Transform & Visualization            
│  │  ├─> transformV2()                                          
│  │  │   ├─> isTableResult() - Identify vector/scalar for table 
│  │  │   ├─> transformDFToTable() - Extract labels as columns   
│  │  │   └─> Set preferredVisualisationType: 'graph'/'table'    
│  │  ├─> decorateWithFrameTypeMetadata()                        
│  │  │   ├─> graphFrames: preferredVisualisationType='graph'    
│  │  │   └─> tableFrames: preferredVisualisationType='table'    
│  │  └─> Render Visualizations                                  
│  │      ├─> Graph Panel: prepareGraphableFields() → uPlot      
│  │      └─> Table Panel: Render with label columns             
│  └─────────────────────────────────────────────────────────────
└────────────────────────────────────────────────────────────────
                              ↓ DataQueryRequest
                              ↑ DataQueryResponse (data.Frame[])
┌────────────────────────────────────────────────────────────────
│                          Grafana Backend                       
│  ┌─────────────────────────────────────────────────────────────
│  │  [REQUEST ↓] Query Processing                               
│  │  ├─> pkg/tsdb/prometheus/Service.QueryData()                
│  │  ├─> promlib/Service.QueryData()                            
│  │  ├─> QueryData.Execute() - Concurrent execution             
│  │  └─> QueryData.handleQuery() - For each query               
│  │      └─> models.Parse() - Parse JSON & interpolate vars     
│  │          ├─> calculatePrometheusInterval()                  
│  │          ├─> InterpolateVariables()                         
│  │          └─> QueryData.fetch() - Concurrent fetching        
│  │              ├─> client.QueryRange() → /api/v1/query_range  
│  │              ├─> client.QueryInstant() → /api/v1/query      
│  │              └─> client.QueryExemplars() → query_exemplars  
│  └─────────────────────────────────────────────────────────────
│                              ↓ HTTP GET/POST                   
│                              ↑ Prometheus JSON Response        
│  ┌─────────────────────────────────────────────────────────────
│  │  [RESPONSE ↑] Data Structure Transform                      
│  │  ├─> parseResponse() - Read HTTP response body              
│  │  ├─> converter.ReadPrometheusStyleResult()                  
│  │  │   └─> jsoniter.Parse() - Stream parse JSON               
│  │  ├─> readPrometheusData() - Read data section               
│  │  ├─> readResult() - Route by resultType                     
│  │  ├─> readMatrixOrVectorMulti() - Convert to frames          
│  │  │   ├─> readTimeValuePair() - Parse timestamps             
│  │  │   ├─> Parse metric labels: {__name__, job, instance}     
│  │  │   ├─> Parse values: [[timestamp, value], ...]            
│  │  │   └─> Create data.Frame:                                 
│  │  │       Fields: [Time field, Value field]                  
│  │  │       Meta: {Type: timeseries-multi/numeric-multi,       
│  │  │              Custom: {resultType: matrix/vector}}        
│  │  ├─> addMetadataToMultiFrame() - Add metadata               
│  │  │   └─> getName() - Apply legend format                    
│  │  └─> processExemplars() - Process exemplar frames           
│  │                                                             
│  │  Return: QueryDataResponse {                                
│  │    Responses: map[refId]DataResponse {                      
│  │      Frames: []data.Frame                                   
│  │    }                                                        
│  │  }                                                          
│  └─────────────────────────────────────────────────────────────
└────────────────────────────────────────────────────────────────
                              ↓ HTTP GET/POST
                              ↑ JSON Response
┌────────────────────────────────────────────────────────────────
│                         Prometheus Server                      
│  ┌─────────────────────────────────────────────────────────────
│  │  [REQUEST ↓] Prometheus API                                 
│  │  ├─> /api/v1/query_range  (range queries)                   
│  │  ├─> /api/v1/query        (instant queries)                 
│  │  └─> /api/v1/query_exemplars (exemplar queries)             
│  └─────────────────────────────────────────────────────────────
│                                                                
│  ┌─────────────────────────────────────────────────────────────
│  │  [RESPONSE ↑] JSON Response                                 
│  │  {                                                          
│  │    "status": "success",                                     
│  │    "data": {                                                
│  │      "resultType": "matrix" | "vector",                     
│  │      "result": [{                                           
│  │        "metric": {"__name__": "up", "job": "prometheus"},   
│  │        "values": [[1234567890, "1"], [1234567891, "1"]]     
│  │      }]                                                     
│  │    }                                                        
│  │  }                                                          
│  └─────────────────────────────────────────────────────────────
└────────────────────────────────────────────────────────────────
```

## 1. Complete Data Flow with Example

### Example Query: `up` in Grafana Explore (Last 5 minutes)

#### Step 1: Frontend Query Initiation

**User Action**: Enter query `up` in Explore and click Run Query

**Frontend Processing** (`packages/grafana-prometheus/src/datasource.ts`):

```typescript
// 1. For Explore, query defaults to both instant and range
getDefaultQuery(app: CoreApp.Explore): PromQuery {
  return {
    refId: 'A',
    expr: 'up',
    instant: true,  // For table
    range: true,    // For graph
  };
}

// 2. Process target and split into two queries
processTargetV2(target: PromQuery, request: DataQueryRequest<PromQuery>) {
  if (target.instant && target.range) {
    // Split into two separate queries
    processedTargets.push(
      {
        ...processedTarget,
        refId: 'A',           // Range query for graph
        instant: false,
        range: true,
      },
      {
        ...processedTarget,
        refId: 'A_instant',   // Instant query for table
        instant: true,
        range: false,
        exemplar: false,
      }
    );
  }
}
```

**HTTP Request to Backend**:
```json
POST /api/ds/query
{
  "queries": [
    {
      "refId": "A",
      "expr": "up",
      "range": true,
      "instant": false,
      "intervalMs": 15000,
      "maxDataPoints": 1000
    },
    {
      "refId": "A_instant",
      "expr": "up",
      "range": false,
      "instant": true,
      "intervalMs": 15000,
      "maxDataPoints": 1000
    }
  ],
  "range": {
    "from": "2025-01-08T10:15:00.000Z",
    "to": "2025-01-08T10:20:00.000Z"
  }
}
```

#### Step 2: Backend Query Processing

**Query Parsing** (`pkg/promlib/models/query.go`):

```go
func Parse(ctx context.Context, query backend.DataQuery, ...) (*Query, error) {
    // 1. Parse JSON query into internal model
    model := &internalQueryModel{}
    json.Unmarshal(query.JSON, model)
    
    // 2. Calculate step interval
    calculatedStep := calculatePrometheusInterval(
        model.Interval,
        dsScrapeInterval,
        int64(model.IntervalMS),
        model.IntervalFactor,
        query,
        intervalCalculator,
    )
    // Result: 15s step
    
    // 3. Interpolate Grafana variables
    expr := InterpolateVariables(
        model.Expr,                    // "up"
        query.Interval,                // 15s
        calculatedStep,                // 15s
        model.Interval,                // 15s
        dsScrapeInterval,              // 15s
        timeRange,                     // 5m
    )
    // Replaces: $__interval, $__range, $__rate_interval, etc.
    
    return &Query{
        Expr:         "up",
        Step:         15 * time.Second,
        Start:        time.Time("2025-01-08T10:15:00Z"),
        End:          time.Time("2025-01-08T10:20:00Z"),
        RefId:        "A",
        RangeQuery:   true,
        InstantQuery: false,
    }, nil
}
```

**Query Execution** (`pkg/promlib/querydata/request.go`):

```go
func (s *QueryData) fetch(ctx context.Context, client *client.Client, q *models.Query) *backend.DataResponse {
    var wg sync.WaitGroup
    dr := &backend.DataResponse{Frames: data.Frames{}}
    
    // Execute both queries concurrently
    if q.RangeQuery {
        wg.Add(1)
        go func() {
            defer wg.Done()
            res := s.rangeQuery(ctx, client, q)
            // HTTP: POST /api/v1/query_range?query=up&start=1704709800&end=1704710100&step=15
            addDataResponse(&res, dr)
        }()
    }
    
    if q.InstantQuery {
        wg.Add(1)
        go func() {
            defer wg.Done()
            res := s.instantQuery(ctx, client, q)
            // HTTP: POST /api/v1/query?query=up&time=1704710100
            addDataResponse(&res, dr)
        }()
    }
    
    wg.Wait()
    return dr
}
```

#### Step 3: Prometheus API Calls

**Range Query Request**:
```http
POST /api/v1/query_range HTTP/1.1
Content-Type: application/x-www-form-urlencoded

query=up&start=1704709800.000&end=1704710100.000&step=15
```

**Range Query Response**:
```json
{
  "status": "success",
  "data": {
    "resultType": "matrix",
    "result": [
      {
        "metric": {
          "__name__": "up",
          "job": "prometheus",
          "instance": "localhost:9090"
        },
        "values": [
          [1704709800, "1"],
          [1704709815, "1"],
          [1704709830, "1"],
          [1704709845, "1"],
          [1704709860, "1"]
        ]
      }
    ]
  }
}
```

**Instant Query Request**:
```http
POST /api/v1/query HTTP/1.1
Content-Type: application/x-www-form-urlencoded

query=up&time=1704710100.000
```

**Instant Query Response**:
```json
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [
      {
        "metric": {
          "__name__": "up",
          "job": "prometheus",
          "instance": "localhost:9090"
        },
        "value": [1704710100, "1"]
      }
    ]
  }
}
```

#### Step 4: Backend Response Parsing and DataFrame Conversion

**Parse Prometheus JSON** (`pkg/promlib/converter/prom.go`):

```go
func ReadPrometheusStyleResult(jIter *jsoniter.Iterator) backend.DataResponse {
    // 1. Parse top-level structure
    for l1Field := iter.ReadObject(); l1Field != ""; l1Field = iter.ReadObject() {
        switch l1Field {
        case "status":
            status = iter.ReadString()  // "success"
        case "data":
            rsp = readPrometheusData(iter, opt)
        case "error":
            promErrString = iter.ReadString()
        case "warnings":
            warnings = readWarnings(iter)
        }
    }
    
    // 2. Parse data section
    for l1Field := iter.ReadObject(); l1Field != ""; l1Field = iter.ReadObject() {
        switch l1Field {
        case "resultType":
            resultType = iter.ReadString()  // "matrix" or "vector"
        case "result":
            rsp = readResult(resultType, rsp, iter, opt, encodingFlags)
        }
    }
    
    return rsp
}

func readMatrixOrVectorMulti(iter *sdkjsoniter.Iterator, resultType string) backend.DataResponse {
    rsp := backend.DataResponse{}
    
    // Iterate through each time series
    for more := iter.ReadArray(); more; more = iter.ReadArray() {
        tempTimes := make([]time.Time, 0)
        tempValues := make([]float64, 0)
        var labels data.Labels
        
        for l1Field := iter.ReadObject(); l1Field != ""; l1Field = iter.ReadObject() {
            switch l1Field {
            case "metric":
                // Parse labels: {"__name__": "up", "job": "prometheus", ...}
                iter.ReadVal(&labels)
                
            case "value":
                // Instant query: single [timestamp, value]
                t, v, _ := readTimeValuePair(iter)
                tempTimes = append(tempTimes, t)
                tempValues = append(tempValues, v)
                
            case "values":
                // Range query: array of [timestamp, value]
                for more := iter.ReadArray(); more; more = iter.ReadArray() {
                    t, v, _ := readTimeValuePair(iter)
                    tempTimes = append(tempTimes, t)
                    tempValues = append(tempValues, v)
                }
            }
        }
        
        // Create DataFrame
        frame := data.NewFrame("",
            data.NewField(data.TimeSeriesTimeFieldName, nil, tempTimes),
            data.NewField(data.TimeSeriesValueFieldName, labels, tempValues),
        )
        
        frame.Meta = &data.FrameMeta{
            Type:        data.FrameTypeTimeSeriesMulti,  // or FrameTypeNumericMulti
            Custom:      map[string]any{"resultType": resultType},
            TypeVersion: data.FrameTypeVersion{0, 1},
        }
        
        if resultType == "vector" {
            frame.Meta.Type = data.FrameTypeNumericMulti
        }
        
        rsp.Frames = append(rsp.Frames, frame)
    }
    
    return rsp
}
```

**Add Metadata** (`pkg/promlib/querydata/response.go`):

```go
func addMetadataToMultiFrame(q *models.Query, frame *data.Frame) {
    // Set interval on time field
    frame.Fields[0].Config = &data.FieldConfig{
        Interval: float64(q.Step.Milliseconds()),  // 15000
    }
    
    // Set display name based on legend format
    customName := getName(q, frame.Fields[1])
    if customName != "" {
        frame.Fields[1].Config = &data.FieldConfig{
            DisplayNameFromDS: customName,
        }
    }
    
    // Set field name from __name__ label
    if n, ok := frame.Fields[1].Labels["__name__"]; ok {
        frame.Fields[1].Name = n  // "up"
    }
}
```

**Backend Response to Frontend**:
```json
{
  "results": {
    "A": {
      "frames": [
        {
          "schema": {
            "refId": "A",
            "meta": {
              "type": "timeseries-multi",
              "custom": {"resultType": "matrix"},
              "executedQueryString": "Expr: up\nStep: 15s"
            },
            "fields": [
              {
                "name": "Time",
                "type": "time",
                "typeInfo": {"frame": "time.Time"},
                "config": {"interval": 15000}
              },
              {
                "name": "up",
                "type": "number",
                "typeInfo": {"frame": "float64"},
                "labels": {
                  "__name__": "up",
                  "job": "prometheus",
                  "instance": "localhost:9090"
                },
                "config": {"displayNameFromDS": "up"}
              }
            ]
          },
          "data": {
            "values": [
              [1704709800000, 1704709815000, 1704709830000, 1704709845000, 1704709860000],
              [1, 1, 1, 1, 1]
            ]
          }
        }
      ]
    },
    "A_instant": {
      "frames": [
        {
          "schema": {
            "refId": "A_instant",
            "meta": {
              "type": "numeric-multi",
              "custom": {"resultType": "vector"}
            },
            "fields": [
              {"name": "Time", "type": "time"},
              {
                "name": "up",
                "type": "number",
                "labels": {
                  "__name__": "up",
                  "job": "prometheus",
                  "instance": "localhost:9090"
                }
              }
            ]
          },
          "data": {
            "values": [
              [1704710100000],
              [1]
            ]
          }
        }
      ]
    }
  }
}
```

#### Step 5: Frontend DataFrame Transformation

**Transform for Visualization** (`packages/grafana-prometheus/src/result_transformer.ts`):

```typescript
export function transformV2(
  response: DataQueryResponse,
  request: DataQueryRequest<PromQuery>,
  options: { exemplarTraceIdDestinations?: ExemplarTraceIdDestination[] }
) {
  // 1. Partition frames by type
  const [tableFrames, framesWithoutTable] = partition<DataFrame>(
    response.data,
    (df) => isTableResult(df, request)
  );
  
  // isTableResult checks:
  // - In Explore: resultType === 'vector' || resultType === 'scalar'
  // - Or: target.format === 'table'
  
  // 2. Transform table frames
  const processedTableFrames = transformDFToTable(tableFrames);
  // Extracts labels as separate columns
  
  // 3. Mark other frames for graph visualization
  const otherFrames = framesWithoutTableHeatmapsAndExemplars.map((dataFrame) => ({
    ...dataFrame,
    meta: {
      ...dataFrame.meta,
      preferredVisualisationType: 'graph',
    },
  }));
  
  return {
    ...response,
    data: [...otherFrames, ...processedTableFrames, ...processedExemplarFrames],
  };
}

export function transformDFToTable(dfs: DataFrame[]): DataFrame[] {
  const frames = refIds.map((refId) => {
    const timeField = getTimeField([]);
    const valueField = getValueField({ data: [], valueName: "Value" });
    const labelFields: Field[] = [];
    
    // Extract all unique labels as separate fields
    dataFramesByRefId[refId].forEach((df) => {
      const promLabels = df.fields[1]?.labels ?? {};
      
      Object.keys(promLabels).sort().forEach((label) => {
        if (!labelFields.some((l) => l.name === label)) {
          labelFields.push({
            name: label,                    // "__name__", "job", "instance"
            config: { filterable: true },
            type: FieldType.string,
            values: [],
          });
        }
      });
    });
    
    // Fill data
    dataFramesByRefId[refId].forEach((df) => {
      const timeFields = df.fields[0]?.values ?? [];
      const dataFields = df.fields[1]?.values ?? [];
      
      timeFields.forEach((value) => {
        timeField.values.push(value);
      });
      
      dataFields.forEach((value) => {
        valueField.values.push(parseSampleValue(value));
        const labelsForField = df.fields[1].labels ?? {};
        labelFields.forEach((field) => 
          field.values.push(getLabelValue(labelsForField, field.name))
        );
      });
    });
    
    // New structure: Time | __name__ | job | instance | Value
    const fields = [timeField, ...labelFields, valueField];
    
    return {
      refId,
      fields,
      meta: {
        preferredVisualisationType: 'rawPrometheus',
      },
      length: timeField.values.length,
    };
  });
  
  return frames;
}
```

#### Step 6: Visualization Rendering

**Explore Routes to Visualizations** (`public/app/features/explore/utils/decorators.ts`):

```typescript
export const decorateWithFrameTypeMetadata = (data: PanelData): ExplorePanelData => {
  const graphFrames: DataFrame[] = [];
  const tableFrames: DataFrame[] = [];
  
  for (const frame of data.series) {
    switch (frame.meta?.preferredVisualisationType) {
      case 'graph':
        graphFrames.push(frame);
        break;
      case 'rawPrometheus':
        tableFrames.push(frame);
        break;
      default:
        if (isTimeSeries(frame)) {
          graphFrames.push(frame);
          tableFrames.push(frame);
        } else {
          tableFrames.push(frame);
        }
    }
  }
  
  return {
    ...data,
    graphFrames,
    tableFrames,
  };
};
```

**Final Rendered Output**:

**Graph Panel** (uses `graphFrames`):
```
Frame Structure:
- Time: [10:15:00, 10:15:15, 10:15:30, 10:15:45, 10:16:00]
- up: [1, 1, 1, 1, 1] with labels: {job: "prometheus", instance: "localhost:9090"}

Renders as: Time series chart with single line
```

**Table Panel** (uses `tableFrames`):
```
Frame Structure:
- Time: [10:16:00]
- __name__: ["up"]
- job: ["prometheus"]
- instance: ["localhost:9090"]
- Value: [1]

Renders as:
| Time      | __name__ | job        | instance        | Value |
|-----------|----------|------------|-----------------|-------|
| 10:16:00  | up       | prometheus | localhost:9090  | 1     |
```

## 2. Key Data Structures

### Backend Data Structures (Go)

#### Query Model (`pkg/promlib/models/query.go`)

```go
// Input query model from frontend
type QueryModel struct {
    PrometheusQueryProperties
    CommonQueryProperties
    
    Expr         string  // PromQL expression
    Range        bool    // Range query flag
    Instant      bool    // Instant query flag
    Exemplar     bool    // Exemplar query flag
    Interval     string  // Query interval
    IntervalMS   float64 // Interval in milliseconds
    LegendFormat string  // Legend template
    UtcOffsetSec int64   // Timezone offset
}

// Internal query after processing
type Query struct {
    Expr          string        // Final PromQL (variables interpolated)
    Step          time.Duration // Calculated step interval
    LegendFormat  string        // Legend template
    Start         time.Time     // Query start time
    End           time.Time     // Query end time
    RefId         string        // Query reference ID
    InstantQuery  bool          // Instant query flag
    RangeQuery    bool          // Range query flag
    ExemplarQuery bool          // Exemplar query flag
    UtcOffsetSec  int64         // Timezone offset
}
```

#### DataFrame Structure (`grafana-plugin-sdk-go/data`)

```go
// Main data structure
type Frame struct {
    Name   string      // Frame name
    Fields []*Field    // Array of fields (columns)
    Meta   *FrameMeta  // Metadata
}

// Field represents a column
type Field struct {
    Name   string              // Field name (e.g., "Time", "Value", "up")
    Type   FieldType           // Field type (time, number, string, etc.)
    Config *FieldConfig        // Display configuration
    Labels Labels              // Prometheus labels (map[string]string)
    Values interface{}         // Actual data values ([]time.Time, []float64, etc.)
}

// Frame metadata
type FrameMeta struct {
    Type                      FrameType             // "timeseries-multi", "numeric-multi", etc.
    TypeVersion               FrameTypeVersion      // Version info
    Custom                    map[string]interface{} // Custom metadata (e.g., {"resultType": "matrix"})
    ExecutedQueryString       string                // Executed query info
    PreferredVisualisationType string               // Preferred visualization
    Notices                   []Notice              // Warnings/errors
}

// Field configuration
type FieldConfig struct {
    DisplayNameFromDS string  // Display name from datasource
    Interval          float64 // Interval for time field (milliseconds)
    Filterable        bool    // Whether field is filterable
}
```

#### DataResponse Structure (`grafana-plugin-sdk-go/backend`)

```go
// Response for a single query
type DataResponse struct {
    Frames      data.Frames   // Array of DataFrames
    Error       error         // Error if any
    Status      Status        // HTTP status code
    ErrorSource ErrorSource   // Error source (downstream, plugin, etc.)
}

// Response for multiple queries
type QueryDataResponse struct {
    Responses map[string]DataResponse  // Map of refId -> DataResponse
}
```

### Frontend Data Structures (TypeScript)

#### Query Model (`packages/grafana-prometheus/src/types.ts`)

```typescript
export interface PromQuery extends DataQuery {
  refId: string;              // Query reference ID
  expr: string;               // PromQL expression
  range?: boolean;            // Range query flag
  instant?: boolean;          // Instant query flag
  exemplar?: boolean;         // Exemplar query flag
  format?: 'time_series' | 'table' | 'heatmap';
  interval?: string;          // Query interval
  intervalFactor?: number;    // Interval factor (deprecated)
  legendFormat?: string;      // Legend template
  step?: number;              // Step in seconds
  hinting?: boolean;          // Query hints enabled
  utcOffsetSec?: number;      // Timezone offset
}
```

#### DataFrame Structure (`@grafana/data`)

```typescript
export interface DataFrame extends QueryResultBase {
  name?: string;               // Frame name
  fields: Field[];             // Array of fields
  length: number;              // Number of rows
  refId?: string;              // Query reference ID
  meta?: QueryResultMeta;      // Metadata
}

export interface Field<T = any> {
  name: string;                // Field name
  type: FieldType;             // Field type (time, number, string, etc.)
  config: FieldConfig;         // Field configuration
  values: T[];                 // Field values
  labels?: Labels;             // Prometheus labels
  state?: FieldState;          // Runtime state
  display?: DisplayProcessor;  // Display processor
}

export interface QueryResultMeta {
  type?: DataFrameType;                        // Frame type
  typeVersion?: FrameTypeVersion;              // Version
  custom?: Record<string, any>;                // Custom metadata
  executedQueryString?: string;                // Executed query
  preferredVisualisationType?: PreferredVisualisationType;  // Preferred viz
  notices?: QueryResultMetaNotice[];           // Warnings/errors
}

export enum FieldType {
  time = 'time',
  number = 'number',
  string = 'string',
  boolean = 'boolean',
  trace = 'trace',
  geo = 'geo',
  other = 'other',
}

export enum DataFrameType {
  TimeSeriesWide = 'timeseries-wide',
  TimeSeriesLong = 'timeseries-long',
  TimeSeriesMulti = 'timeseries-multi',
  NumericWide = 'numeric-wide',
  NumericMulti = 'numeric-multi',
  NumericLong = 'numeric-long',
  HeatmapRows = 'heatmap-rows',
  HeatmapCells = 'heatmap-cells',
}
```

#### DataQueryResponse Structure

```typescript
export interface DataQueryResponse {
  data: DataFrame[];           // Array of DataFrames
  state?: LoadingState;        // Loading state
  error?: DataQueryError;      // Error if any
  errors?: DataQueryError[];   // Multiple errors
  request?: DataQueryRequest;  // Original request
  traceIds?: string[];         // Trace IDs
}
```

## 3. Summary

The Grafana Prometheus datasource flow involves:

1. **Frontend**: Query processing, splitting instant+range queries, variable interpolation
2. **Backend**: Query parsing, concurrent execution, HTTP client communication
3. **Prometheus**: API endpoints returning JSON responses
4. **Backend Parsing**: Efficient JSON parsing to DataFrame conversion
5. **Frontend Transformation**: Restructuring DataFrames for different visualizations
6. **Visualization**: Rendering graphs and tables from optimized DataFrame structures

The key innovation is:
- **Backend** returns different frame types (`timeseries-multi` vs `numeric-multi`) based on query type
- **Frontend** performs additional transformation to extract labels as columns for table display
- **Concurrent execution** of range and instant queries for Explore
- **Efficient parsing** using jsoniter for high performance
- **Flexible visualization** with frames marked by `preferredVisualisationType`

## Reference
- https://grafana.com/developers/dataplane/dataplane-dataframes
- https://github.com/grafana/grafana
