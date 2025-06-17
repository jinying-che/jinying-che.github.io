---
title: "How the service is discovered in k8s"
date: "2025-03-28T09:44:33+08:00"
tags: ["k8s"]
description: "service discovery overview"
---

# Fundamentals
## kube-proxy x iptables

## kube-proxy x ipvs

# Diagram
```txt

                            +--------------------------+
                            |   External User (Browser)|
                            +--------------------------+
                                        |
                             HTTP/HTTPS to NodeIP:NodePort
                                        |
                                [ Kubernetes Node ]
                                        |
                        +-----------------------------------+
                        |  NodePort Service (Ingress-NGINX) | 
                        |  Type: NodePort                   | 
                        |  Ports: 80 → 30080, 443 → 30443   |
                        +-----------------------------------+
                                        |
                          [ Ingress-NGINX Controller Pod ]
                          (nginx reverse proxy running in pod)
                                        |
                          Matches Ingress rules like:
                            - Host: app.example.com
                            - Path: /api → service/api
                                        |
                      +----------------+----------------+
                      |                                 |
            [ Service: frontend-svc ]        [ Service: api-svc ]
                      |                                 |
                  [ Pod(s): frontend ]           [ Pod(s): backend ]
```

# What is Ingress?
Ingress is a Kubernetes API object that manages external access to services, typically use HTTP or HTTP/S service.
It allows you to define rules for routing external traffic to internal services.
But Ingress is just a **configuration**, it doesn’t do the actual routing.

That’s where the Ingress Controller comes in.

# What is an Ingress Controller?
An Ingress Controller is a specialized Kubernetes component (usually deployed as a pod) that implements the rules defined in Ingress resources.

> In other words:
> 
> An Ingress defines what traffic should go where, and the Ingress Controller is the component that makes it happen.

### Key Roles of an Ingress Controller
|Role|Description|
|---|---|
|💬 Listens for Ingress resources | Watches the Kubernetes API for any Ingress definitions |
|⚙️ Builds a routing config | Dynamically builds a reverse proxy configuration (e.g., NGINX, HAProxy) |
|🚦 Handles external traffic | Exposes itself (via NodePort/LoadBalancer) to accept requests from the outside |
|🚚 Routes traffic to services | Based on domain/path rules in Ingress resources |
|🔐 Can handle HTTPS & TLS | Supports automatic TLS with cert-manager or manual certs |
|🔍 Supports advanced rules	| Path rewrites, custom headers, authentication, rate-limiting, etc. |
### common ingress controller:
- [ingress-nginx](https://github.com/kubernetes/ingress-nginx/tree/main): ingress-nginx is an Ingress controller for Kubernetes using NGINX as a reverse proxy and load balancer

for example, you can run the following command to install ingress-nginx conroller:
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.0/deploy/static/provider/cloud/deploy.yaml

# This sets up:
# - A Pod that runs the NGINX controller.
# - A Service (usually LoadBalancer or NodePort) to expose NGINX to the internet.
```

### How to Inspect the Ingress Nginx Controller
```bash
# get ingress
sudo kubectl get ingress -n namespace

# describe ingress
sudo kubectl describe ingress -n namespace

# get all deployment (-A is equal to --all-namespaces)
sudo kubectl get deployment -A

# get ingress deployment
sudo kubectl get deployment ingress_name -n namespace -o yaml
```

# What is a NodePort in Kubernetes?
A NodePort is a type of Kubernetes **Service** that exposes an application running in the cluster on a static port on every node’s IP address.

> In simple terms:
> NodePort maps a port on your Kubernetes node (like 30080) to a pod running inside the cluster.

## How to Check the NodePort for Ingress-NGINX
```bash
# Get the NodePort for the ingress-nginx Service (-n ingress-namespace)
sudo kubectl get svc -n ingress-nginx 

# output means you can access ingress-nginx-controller (pod) port 80 via node (host) port 30080 (http), and port 443 via 30443 (https)
# for example, if the node ip is 192.168.1.10, you can access ingress-nginx-controller via:
# http://192.168.1.10:30080
# https://192.168.1.10:30443
NAME                                 TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)                      AGE
ingress-nginx-controller             NodePort    10.99.184.72     <none>        80:30080/TCP,443:30443/TCP   3d


```
