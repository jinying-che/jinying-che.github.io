---
title: "JWT"
date: "2025-12-29T14:41:02+08:00"
tags: ["jwt"]
description: "json web token overview"
---

## What is JWT (JSON Web Token)?
JSON Web Token (JWT) is an open standard ([RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519)) that defines a compact and self-contained way for securely transmitting information between parties as a JSON object. This information can be verified and trusted because it is digitally signed. JWTs can be signed using a secret (with the HMAC algorithm) or a public/private key pair using RSA or ECDSA.


## What is the JSON Web Token structure?
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
└─────────── Header ───────────────┘└───────────── Payload ───────────────────────┘└─────────── Signature ─────────────────┘
```
In its compact form, JSON Web Tokens consist of three parts separated by dots (.), which are:
- **Header**: (base64 encoded): Algorithm + token type
    ```
    {"alg": "HS256", "typ": "JWT"}
    ```
- **Payload**: Payload (base64 encoded): Claims/data
    ```
    {"sub": "user123", "name": "John", "exp": 1735500000}
    ```
- **Signature**: Created by signing base64(header) + "." + base64(payload) with a secret key (**which is a global private key in server applying for all clients**)

## How does JSON Web Token work?
```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           JWT AUTHENTICATION FLOW                            │
└──────────────────────────────────────────────────────────────────────────────┘

    CLIENT                                                 SERVER
       │                                                      │
       │  1. LOGIN REQUEST                                    │
       │  ─────────────────────────────────────────────────►  │
       │  POST /login                                         │
       │  { "username": "john", "password": "secret" }        │
       │                                                      │  2. VALIDATE
       │                                                      │     CREDENTIALS
       │                                                      │     ↓
       │                                                      │  3. GENERATE JWT
       │                                                      │     (sign with secret)
       │  4. RETURN JWT TOKEN                                 │
       │  ◄─────────────────────────────────────────────────  │
       │  { "token": "eyJhbGci..." }                          │
       │                                                      │
       │                                                      │
       │  5. API REQUEST WITH TOKEN                           │
       │  ─────────────────────────────────────────────────►  │
       │  GET /api/protected-resource                         │
       │  Header: Authorization: Bearer eyJhbGci...           │
       │                                                      │  6. VERIFY JWT
       │                                                      │     - Check signature
       │                                                      │     - Check expiration
       │                                                      │     - Extract user info
       │  7. RETURN PROTECTED DATA                            │
       │  ◄─────────────────────────────────────────────────  │
       │  { "data": "secret stuff" }                          │
       │                                                      │

```
## References
- https://www.jwt.io/introduction#what-is-json-web-token
