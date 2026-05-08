---
title: "k8s Playground: Building a Full 3-Tier App from Scratch"
date: "2026-05-08T11:27:57+0800"
tags: ["kubernetes", "demo", "mysql", "react", "nginx", "ghcr"]
description: "A hands-on walkthrough of Kubernetes core functions by building and deploying a custom 3-tier application."
draft: true
---

# Overview

Setting up a cluster is only 10% of the journey. The real magic happens when you deploy applications. This "Playground" guide walks you through a full-stack deployment, from writing the code to scaling it in production.

We will build a **3-Tier Application**:
1.  **Frontend**: A modern React/Vue interface served by Nginx.
2.  **Backend**: A REST API (Go/Python/Node) that processes logic.
3.  **Database**: A MySQL instance with persistent storage.

---

# ⚠️ Prerequisites: Part 2 Addons

To finish this demo, you must have completed **Part 2** of the cluster setup:
*   **Storage**: A `StorageClass` (like `local-path`) must be installed for Phase 2.
*   **Ingress**: A Gateway or Ingress controller (like Traefik) is needed to reach your apps from the internet.

---

# Phase 0: The Image Registry (GHCR)

Since we are building our own images, we need a place to store them so the Kubernetes node can download (pull) them. We will use **GitHub Container Registry (GHCR)**.

### 1. Authenticate with GitHub
You'll need a [Personal Access Token (classic)](https://github.com/settings/tokens) with `write:packages` permissions.
```bash
export CR_PAT=YOUR_TOKEN
echo $CR_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

### 2. The Build & Push Loop
For every component we build, the workflow is:
```bash
# Build for your Pi's architecture (ARM64)
docker build -t ghcr.io/YOUR_USERNAME/IMAGE_NAME:v1 .

# Push to the cloud
docker push ghcr.io/YOUR_USERNAME/IMAGE_NAME:v1
```

---

# Phase 1: The Engine (The Backend)

We start with the API. It serves as the "brain" of the operation.

### 1. Build the API
Create a simple API that returns a JSON response. Build and push it as `ghcr.io/username/api:v1`.

### 2. Deploy to K8s
```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: ghcr.io/YOUR_USERNAME/api:v1
        ports:
        - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: api-service
spec:
  selector:
    app: api
  ports:
  - port: 80
    targetPort: 8080
```

---

# Phase 2: The Memory (Persistent MySQL)

Databases are "Stateful." If the Pod dies, we don't want to lose the data.

### 1. Create a Secret
Never hardcode passwords in YAML. Use a Secret:
```bash
kubectl create secret generic mysql-pass --from-literal=password=YOUR_PASSWORD
```

### 2. Deploy with Persistence
```yaml
# mysql.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-pvc
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 2Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mysql
spec:
  template:
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-pass
              key: password
        volumeMounts:
        - name: mysql-data
          mountPath: /var/lib/mysql
      volumes:
      - name: mysql-data
        persistentVolumeClaim:
          claimName: mysql-pvc
```

---

# Phase 3: The Connection (Service Discovery)

How does the API find MySQL? We use the Service name. 
In your API code, the database connection string should look like:
`mysql.default.svc.cluster.local` (or simply `mysql`).

Kubernetes has a built-in **CoreDNS** that automatically maps Service names to their internal IP addresses.

---

# Phase 4: Resilience (Scaling & Healing)

### 1. Self-Healing
Manually kill a Backend Pod:
```bash
kubectl delete pod <api-pod-name>
```
Watch how Kubernetes immediately detects the missing replica and spins up a new one to maintain your "desired state."

### 2. Horizontal Scaling (HPA)
If your API gets too much traffic, K8s can scale automatically based on CPU usage. 

**Note:** This requires the `metrics-server` addon from Part 2.

```bash
kubectl autoscale deployment api-server --cpu-percent=50 --min=2 --max=10
```

---

# Phase 5: The Interface (Modern Frontend)

We use a modern FE stack (React/Vue/Next) and serve it using Nginx.

### 1. Multi-Stage Docker Build
To keep images small, we build the code in one container and serve the static files in a tiny Nginx container.

```dockerfile
# stage 1: build
FROM node:18 AS build
WORKDIR /app
COPY . .
RUN npm install && npm run build

# stage 2: serve
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

### 2. Avoiding CORS
Configure Nginx to proxy `/api` requests to your Backend Service:
```nginx
location /api/ {
    proxy_pass http://api-service/;
}
```

---

# Conclusion

By completing these 5 phases, you've moved from a simple server to a **production-ready 3-tier architecture**. You are now using:
*   **Deployments** for running code.
*   **Services** for internal discovery.
*   **PVCs** for persistent data.
*   **Secrets** for security.
*   **HPA** for scalability.
*   **GHCR** for custom image management.

# References

## Kubernetes Concepts
*   [Deployments - Running your app](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
*   [Services - Networking & Discovery](https://kubernetes.io/docs/concepts/services-networking/service/)
*   [Persistent Volumes & PVCs](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
*   [Secrets - Managing Credentials](https://kubernetes.io/docs/concepts/configuration/secret/)
*   [Horizontal Pod Autoscaler (HPA)](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)

## Tools & Registry
*   [GitHub Container Registry (GHCR) Guide](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
*   [Docker Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
*   [Nginx Proxy Pass Documentation](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass)
