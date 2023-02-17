---
title: "API Design"
date: "2023-02-13T22:27:32+08:00"
tags: ["api", "design"]
description: "Some ideas you should know when talking about API Design"
---

There are some similar technologies as Rest, OpenAPI, gRPC and GraphQL which are popular design or standard or framework that related to API design, meanwhile, they are prone to make people confused for the use case. 

Simple Put:
- `REST` is a software **architectural** and common communication **standard**.
- `OpenAPI` is a **specification**, which defines a standard, programming language-agnostic interface description for HTTP APIs.
- `gRPC` is a high performance Remote Procedure Call (RPC) **framework**.
- `GraphQL` is a **query language** for your API. 

## 1. Rest
Representational state transfer (REST) is a software architectural style that describes a uniform interface between physically separate components, often across the Internet in a client-server architecture.

REST is the most common communication standard between computers over the internet, an API that follows the REST standard is called a RESTful API.

### 1.1 Architectural Constraints
- Client–server architecture
- Statelessness
- Cacheability
- Layered system
- Code on demand (optional)
- Uniform interface
> refer to [wikipedia](https://en.wikipedia.org/wiki/Representational_state_transfer#Architectural_constraints) for more details

### 1.2 Applied to web services
- a base URI, such as http://api.example.com/
- standard HTTP methods (e.g., GET, POST, PUT, and DELETE)
- a media type that defines state transition data elements 

### 1.3 CRUD
- POST   --> CREATE *(non-idempotent)*
- GET    --> READ   *(idempotent)*
- PUT    --> UPDATE *(idempotent)*
- DELETE --> DELETE *(idempotent)*

### 1.4 Version
Versioning allows an implementation to provide backward compatibility so that if we introduce breaking changes from one version to another, consumers get enough time to move to the next version.

There are many ways to version an API. The most straightforward is to prefix the version before the resource on the URI. For instance:

- https://shopee.com/v1/products
- https://shopee.com/v2/products

### 1.5 Example
This API has four endpoints:

- POST `/users` Creates a new user with the specified name and email.
- GET `/users/:id` Retrieves an existing user with the specified ID.
- PUT `/users/:id` Updates an existing user with the specified ID.
- DELETE `/users/:id` Deletes an existing user with the specified ID.

```sh
POST /users
{
  "name": "John Smith",
  "email": "john@example.com"
}

GET /users/:id

PUT /users/:id
{
  "name": "John Smith",
  "email": "john@example.com"
}

DELETE /users/:id

```

## 2. gRPC
1. gPRC is an implementation of Remote Procedure Call (RPC) 
2. It is modern open source high performance RPC framework that can run in any environment.

> RPC (Remote Procedure Call) is called “remote” because it enables communications between remote services when services are deployed to different servers under microservice architecture. From the user’s point of view, it acts like a local function call.

### 2.1 Core Concepts
- Design service API using [protocol buffers](https://developers.google.com/protocol-buffers) as Interface Definition Language (IDL)
- protocol buffers TODO?
- gRPC builds on [HTTP/2](https://www.rfc-editor.org/rfc/rfc7540) long-lived connections for inter-service communication

### 2.2 Overall
![gprc overall](/images/grpc_overall.jpeg)

### 2.3 Quick Start
- https://grpc.io/docs/languages/go/quickstart/


## 3. OpenAPI
First of all, I'd like to recommend to take an overview of some [examples](https://github.com/OAI/OpenAPI-Specification/tree/main/examples) for OpenAPI Spec. For details, can read the [basic structure](https://swagger.io/docs/specification/basic-structure/)

1. The OpenAPI Specification (OAS) defines an **interface description** for HTTP APIs
2. It's tend to be industry standard  
3. It's programming language-agnostic
4. Both human and computers can understand and discover the capabilities of a service 
5. It removes the guesswork in calling a service and saves the communication effort
6. Consumer can interact the remote service with minimal implementation logic (with the rich [OpenAPI Tools](https://openapi.tools))
7. It boost the [API driven development](https://swagger.io/resources/articles/adopting-an-api-first-approach/)
8. It supports Restful API
8. The OpenAPI doc are represented in YAML or JSON format which may be produced and served statically or **generated dynamically** from an application. (e.g. [generate RESTful API documentation with Swagger 2.0 for Go](https://github.com/swaggo/swag))

Generally, we would have the best practice in API desgin as long as we follow the OAS and use the related toolset.
### 3.1 What we can do with OpenAPI Spec
1. Interactive documentation 
2. Code generation for documentation, clients, and servers 
3. automation of test cases
4. etc.

### 3.2 Quick Start
#### 3.2.1 API Definition
API is a contract followed by all stakeholders across the whole organization, traditionally, two main approaches exist when creating OpenAPI documents: Code-first and Design-first.

##### Design First
API Design First approach is being more and more pupular to build systems today as it provides many [benefits](https://swagger.io/resources/articles/adopting-an-api-first-approach/#the-benefits-of-an-api-first-approach-2).

To design the API from the scratch, we can use [swagger editor](https://swagger.io/tools/swagger-editor/) to create API in an interactive way where you can see if your changes is valid and what they would like in the real time. Personal speaking, learning by doing is the best way to understand and write OpenAPI docs, you can simply import and update the example like `Petstore` in the editor and kick off your OpenAPI journey.

##### Code First
Code First is possibly adopted by some devs for some fast and easy API building, whereas it's an old school and not recommeded at all, unless you have an exist project which requires to follow the OpenAPI spec after the code has been finished already, with that saying, there are some tools like [go-swagger](https://github.com/go-swagger/go-swagger) to generate OpenAPI documents automatically by parsing code annotations.

#### 3.2.2 Code Generation
Once we got the standard OpenAPI docs from wherever it's generated from the code or created by any stakeholders, there are some tools for you to generate the code, for example:
>[OpenAPI Generator](https://openapi-generator.tech/) - A template-driven engine to generate documentation, API clients and server stubs in different languages by parsing your OpenAPI Description (community-driven fork of swagger-codegen)

#### 3.3.3 Mock Server and Testing 
TBD

## 4. Reference
#### Rest
- https://blog.bytebytego.com/p/why-is-restful-api-so-popular
- https://en.wikipedia.org/wiki/Representational_state_transfer
- [gRPC vs REST: Understanding gRPC, OpenAPI and REST and when to use them in API design](https://cloud.google.com/blog/products/api-management/understanding-grpc-openapi-and-rest-and-when-to-use-them)
#### gRPC
- https://blog.bytebytego.com/i/84137023/how-does-grpc-work
- https://grpc.io/blog/grpc-on-http2/
#### OpenAPI
- https://spec.openapis.org/oas/v3.1.0
- [Better API Design With OpenAPI](https://www.youtube.com/watch?v=uBs6dfUgxcI)
- https://github.com/OAI/OpenAPI-Specification/
- https://swagger.io/resources/articles/adopting-an-api-first-approach/
- Examples: https://github.com/OAI/OpenAPI-Specification/tree/main/examples
- Best Practice: https://oai.github.io/Documentation/best-practices.html
