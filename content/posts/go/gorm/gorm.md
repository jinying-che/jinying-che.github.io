---
title: "GORM"
date: "2024-03-16T17:19:46+08:00"
tags: ["golang", "lib"]
description: "Deep into https://github.com/go-gorm/gorm"
---

### Source Code
When you run CRUD interface by gorm, what happened inside isn't that straightforward, let's take a look!

##### 1. Basic gorm usage
```go
func main() {
	users := []User{
		{Name: "Jinzhu", Age: 18},
		{Name: "Jackson", Age: 19},
	}
	db.Create(users) // pass a slice to insert multiple row

	user := User{Name: "Jinzhu", Age: 18}
	db.Find(user)
	db.Updates(user)
	db.Delete(user)
}
```
##### 2. Flow of the function, e.g. `db.Find()`:
```go
// gorm.io/finisher_api.go
func (db *DB) Find(dest interface{}, conds ...interface{}) (tx *DB) {
	...

	return tx.callbacks.Query().Execute(tx)
}
```
```go
// gorm.io/callbacks.go
func (cs *callbacks) Query() *processor {
	return cs.processors["query"]
}

func (p *processor) Execute(db *DB) *DB {
    ...
	for _, f := range p.fns {
		f(db)
	}
    ...
	return db
}

type processor struct {
	db        *DB
	Clauses   []string
	fns       []func(*DB)
	callbacks []*callback
}
```

##### 3. Where is the `processor.fns`?
```go
// gorm.io/callbacks.go
func (p *processor) compile() (err error) {
    ...
	if p.fns, err = sortCallbacks(p.callbacks); err != nil {
		p.db.Logger.Error(context.Background(), "Got error when compile callbacks, got %v", err)
	}
	return
}

func (c *callback) Register(name string, fn func(*DB)) error {
    ...
	c.processor.callbacks = append(c.processor.callbacks, c)
	return c.processor.compile()
}
```

##### 4. Who will register the callback?
```go
// gorm.io/callbacks/callbacks.go
func RegisterDefaultCallbacks(db *gorm.DB, config *Config) {
    ...
	createCallback := db.Callback().Create()
	createCallback.Match(enableTransaction).Register("gorm:begin_transaction", BeginTransaction)
	createCallback.Register("gorm:before_create", BeforeCreate)
	createCallback.Register("gorm:save_before_associations", SaveBeforeAssociations(true))
	createCallback.Register("gorm:create", Create(config))
	createCallback.Register("gorm:save_after_associations", SaveAfterAssociations(true))
	
    createCallback.Register()
    queryCallback.Register()
    updateCallback.Register()
    deleteCallback.Register()
    ...
}
```

##### 5. Who will call `RegisterDefaultCallbacks`?
The answer is in `"gorm.io/driver/mysql"` instead of `"gorm.io/gorm"`:
```go
// gorm.io/gorm.go
func Open(dialector Dialector, opts ...Option) (db *DB, err error) {
    ...
    if config.Dialector != nil {
		err = config.Dialector.Initialize(db)
	}
    ...
}
```

```go
// gorm.io/driver/mysql@v1.5.4/mysql.go
func (dialector Dialector) Initialize(db *gorm.DB) (err error) {

	callbacks.RegisterDefaultCallbacks(db, callbackConfig)
}

```

### End Of The Story
ORM framework is relative complex, too much details to understand. Dig into the key design and path, don't get bogged down in the details. 


## Referrence
- https://github.com/go-gorm/gorm
