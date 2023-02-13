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


## 3. OpenAPI
1. The OpenAPI Specification (OAS) defines an **interface description** for HTTP APIs
2. It's tend to be industry standard  
3. It's programming language-agnostic
4. Both human and computers can understand and discover the capabilities of a service 
5. It removes the guesswork in calling a service and saves the communication effort
6. Consumer can interact the remote service with minimal implementation logic (with the rich [OpenAPI Tools](https://openapi.tools))
7. It boost the [API driven development](https://swagger.io/resources/articles/adopting-an-api-first-approach/)
8. It supports Restful API
8. The OpenAPI doc are represented in YAML or JSON format which may be produced and served statically or **generated dynamically** from an application. (e.g. [generate RESTful API documentation with Swagger 2.0 for Go](https://github.com/swaggo/swag))

### 3.1 What we can do with OpenAPI Spec
1. Interactive documentation 
2. Code generation for documentation, clients, and servers 
3. automation of test cases
4. etc.

## 4. Demo
1. [REST API](rest_api)
2. [gRPC](grpc/go)
3. [OpenAPI](openapi)

## 5. Reference
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
