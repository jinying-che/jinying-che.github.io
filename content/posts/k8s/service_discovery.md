---
title: "How the service is discovered in k8s"
date: "2025-03-28T09:44:33+08:00"
tags: ["k8s"]
description: "service discovery overview"
draft: true
---

# Fundamentals
## kube-proxy x iptables

## kube-proxy x ipvs

# What is Ingress?
Ingress is a Kubernetes API object that manages external access to services, typically use HTTP or HTTP/S service.
It allows you to define rules for routing external traffic to internal services.
But Ingress is just a **configuration**, it doesn’t do the actual routing.

That’s where the Ingress Controller comes in.

# Ingress Controller
common ingress controller:
- [ingress-nginx](https://github.com/kubernetes/ingress-nginx/tree/main): ingress-nginx is an Ingress controller for Kubernetes using NGINX as a reverse proxy and load balancer

# Command
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
A NodePort is a type of Kubernetes Service that exposes an application running in the cluster on a static port on every node’s IP address.

> In simple terms:
> NodePort maps a port on your Kubernetes node (like 30080) to a pod running inside the cluster.
