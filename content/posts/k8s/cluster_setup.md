---
title: "k8s cluster setup on a single server"
date: "2026-03-22T09:00:00+08:00"
tags: ["kubernetes", "k8s"]
description: "production-style kubernetes cluster on a single server using kubeadm"
draft: false
---

# Overview

Running a full k8s cluster on a single server — useful for homelab, dev environment, or small-scale production.

**Tool choice: kubeadm vs k3s**

| | kubeadm | k3s |
|---|---|---|
| Philosophy | "Real" k8s, full control | Lightweight, batteries-included |
| Binary size | Multiple components | Single binary (~70MB) |
| etcd | Requires separate install | Embedded SQLite or etcd |
| Setup effort | More manual | Much simpler |
| Good for | Learning the internals | Production single-node fast setup |

This guide uses **kubeadm** (closer to how multi-node production clusters are set up). For a faster path, see the k3s section at the bottom.

**Stack we'll set up:**

```
┌─────────────────────────────────────────────┐
│              Single Server                  │
│                                             │
│  ┌─────────────┐   ┌─────────────────────┐  │
│  │ Control     │   │ Worker (same node)  │  │
│  │ Plane       │   │                     │  │
│  │             │   │  App Pods           │  │
│  │ apiserver   │   │  Ingress Controller │  │
│  │ etcd        │   │  Monitoring stack   │  │
│  │ scheduler   │   │                     │  │
│  │ controller  │   │                     │  │
│  └─────────────┘   └─────────────────────┘  │
│                                             │
│  CNI: Flannel          Storage: local-path  │
│  Ingress: nginx        TLS: cert-manager    │
└─────────────────────────────────────────────┘
```

**Minimum requirements:** 2 vCPU, 4GB RAM, 20GB disk, Ubuntu 22.04

---

# 1. Prepare the Server

## Disable swap (k8s requires this)

```bash
swapoff -a
# make permanent
sed -i '/swap/d' /etc/fstab
```

## Load required kernel modules

```bash
cat <<EOF | tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

modprobe overlay
modprobe br_netfilter
```

## Set sysctl params

```bash
cat <<EOF | tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sysctl --system
```

---

# 2. Install Container Runtime (containerd)

```bash
# install containerd
apt-get update
apt-get install -y containerd

# generate default config
mkdir -p /etc/containerd
containerd config default | tee /etc/containerd/config.toml

# enable SystemdCgroup (required for k8s)
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

systemctl restart containerd
systemctl enable containerd
```

---

# 3. Install kubeadm, kubelet, kubectl

```bash
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gpg

curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | \
  gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | \
  tee /etc/apt/sources.list.d/kubernetes.list

apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl   # prevent auto-upgrades
```

---

# 4. Initialize the Cluster

```bash
kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \     # flannel default
  --apiserver-advertise-address=<YOUR_SERVER_IP>
```

**What happens during init:**
```
[preflight]      → checks: swap off, ports free, kernel params set
[certs]          → generates CA + all component certs
[kubeconfig]     → creates kubeconfig for admin, kubelet, controller, scheduler
[etcd]           → starts etcd as a static Pod
[control-plane]  → starts apiserver, controller-manager, scheduler as static Pods
[addons]         → installs CoreDNS and kube-proxy
```

Save the `kubeadm join` token printed at the end (needed if you add nodes later).

## Set up kubeconfig

```bash
mkdir -p $HOME/.kube
cp /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config
```

## Allow scheduling on control-plane node (single-server only)

By default, control plane nodes are tainted — no workloads can run there. Remove the taint:

```bash
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

Verify the node is Ready:
```bash
kubectl get nodes
# NAME     STATUS     ROLES           AGE   VERSION
# server   NotReady   control-plane   30s   v1.30.x
# (NotReady because CNI not installed yet)
```

---

# 5. Install CNI Plugin (Flannel)

Flannel provides the flat Pod network k8s requires.

```bash
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
```

Wait for node to become Ready:
```bash
kubectl get nodes -w
# NAME     STATUS   ROLES           AGE   VERSION
# server   Ready    control-plane   2m    v1.30.x
```

Verify system pods:
```bash
kubectl get pods -n kube-system
# coredns, etcd, kube-apiserver, kube-controller-manager,
# kube-proxy, kube-scheduler, kube-flannel should all be Running
```

---

# 6. Storage: local-path-provisioner

Rancher's local-path-provisioner gives you dynamic PV provisioning using local disk — simplest option for a single server.

```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml

# set as default StorageClass
kubectl patch storageclass local-path \
  -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

Test it:
```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
EOF

kubectl get pvc test-pvc
# STATUS should be Bound
kubectl delete pvc test-pvc
```

---

# 7. Ingress Controller (nginx)

Exposes HTTP/HTTPS services to the outside.

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/baremetal/deploy.yaml
```

For a single server, expose it via NodePort (or HostPort). Check the assigned ports:
```bash
kubectl get svc -n ingress-nginx
# ingress-nginx-controller  NodePort  ...  80:3XXXX/TCP,443:3XXXX/TCP
```

To use standard ports 80/443, set up a host-level redirect or use a DaemonSet with hostPort. Easier: point your server's port 80/443 to the NodePort via iptables:

```bash
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port <node-port-80>
iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port <node-port-443>
```

---

# 8. TLS: cert-manager

Automates TLS certificate issuance from Let's Encrypt.

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml

# wait for it to be ready
kubectl -n cert-manager rollout status deploy/cert-manager
```

Create a ClusterIssuer for Let's Encrypt:

```yaml
# cluster-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your@email.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

```bash
kubectl apply -f cluster-issuer.yaml
```

Now any Ingress can get automatic TLS:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts: [myapp.example.com]
    secretName: myapp-tls
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: myapp
            port:
              number: 80
```

---

# 9. Metrics Server (for kubectl top)

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

For a single server (often uses self-signed certs), patch to skip TLS verification:
```bash
kubectl patch deployment metrics-server -n kube-system \
  --type json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```

Verify:
```bash
kubectl top nodes
kubectl top pods -A
```

---

# Deploy a Test App

Verify the whole stack works end-to-end:

```yaml
# test-app.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: whoami
spec:
  replicas: 2
  selector:
    matchLabels:
      app: whoami
  template:
    metadata:
      labels:
        app: whoami
    spec:
      containers:
      - name: whoami
        image: traefik/whoami
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: whoami
spec:
  selector:
    app: whoami
  ports:
  - port: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: whoami
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts: [whoami.example.com]
    secretName: whoami-tls
  rules:
  - host: whoami.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: whoami
            port:
              number: 80
```

```bash
kubectl apply -f test-app.yaml
kubectl get pods,svc,ingress
# then: curl https://whoami.example.com
```

---

# Cluster State Summary

After all steps, you should have:

```bash
kubectl get pods -A
# NAMESPACE       NAME                                      READY   STATUS
# cert-manager    cert-manager-xxx                          1/1     Running
# cert-manager    cert-manager-cainjector-xxx               1/1     Running
# cert-manager    cert-manager-webhook-xxx                  1/1     Running
# ingress-nginx   ingress-nginx-controller-xxx              1/1     Running
# kube-flannel    kube-flannel-ds-xxx                       1/1     Running
# kube-system     coredns-xxx (x2)                          1/1     Running
# kube-system     etcd-xxx                                  1/1     Running
# kube-system     kube-apiserver-xxx                        1/1     Running
# kube-system     kube-controller-manager-xxx               1/1     Running
# kube-system     kube-proxy-xxx                            1/1     Running
# kube-system     kube-scheduler-xxx                        1/1     Running
# kube-system     metrics-server-xxx                        1/1     Running
# local-path-storage local-path-provisioner-xxx             1/1     Running
```

---

# k3s Alternative (Faster Path)

If you want the same result in 2 minutes:

```bash
curl -sfL https://get.k3s.io | sh -

# kubeconfig
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# k3s includes: flannel, local-path-provisioner, metrics-server, traefik ingress
# just add cert-manager on top
```

k3s trades transparency for simplicity. Good for production single-node; kubeadm is better for learning internals or planning multi-node expansion.

---

# Upgrades

kubeadm upgrades follow a strict process — never skip minor versions (1.29 → 1.30 → 1.31, not 1.29 → 1.31):

```bash
# 1. upgrade kubeadm
apt-get install -y kubeadm=1.31.x-*

# 2. check the upgrade plan
kubeadm upgrade plan

# 3. apply
kubeadm upgrade apply v1.31.x

# 4. upgrade kubelet + kubectl
apt-get install -y kubelet=1.31.x-* kubectl=1.31.x-*
systemctl restart kubelet
```
