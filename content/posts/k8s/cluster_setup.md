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

# 1. Prepare the Server

> **Doc:** [kubeadm install — Before you begin](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/#before-you-begin)
>
> **Why:** k8s has strict requirements on the host OS before kubelet can run. These three steps (swap, kernel modules, sysctl) are all preflight checks that `kubeadm init` will validate — failing any of them will abort the init.

## Disable swap

kubelet refuses to start if swap is enabled by default. The reason: k8s resource scheduling assumes memory limits are hard — swap breaks that guarantee because a container can silently exceed its memory limit by paging to disk, making OOM decisions unpredictable.

```bash
swapoff -a
# make permanent across reboots
sed -i '/swap/d' /etc/fstab
```

> **k8s 1.28+ note:** Swap support is now available as a stable feature. You can keep swap enabled by setting `failSwapOn: false` and `memorySwap.swapBehavior: NoSwap` in KubeletConfiguration — but disabling swap is still the simplest and most compatible path.

## Load required kernel modules

`overlay` is needed for overlayfs (container image layers). `br_netfilter` allows iptables to see bridged traffic — required for kube-proxy to intercept Pod-to-Pod packets crossing the bridge.

```bash
cat <<EOF | tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

modprobe overlay
modprobe br_netfilter
```

## Set sysctl params

These ensure iptables rules apply to bridged traffic (not just routed traffic) and that the node can forward packets between Pods on different nodes.

```bash
cat <<EOF | tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sysctl --system
```

# 2. Install Container Runtime (containerd)

> **Doc:** [Container runtimes — containerd](https://kubernetes.io/docs/setup/production-environment/container-runtimes/#containerd)
>
> **Why:** k8s doesn't run containers directly — it delegates to a container runtime via the CRI (Container Runtime Interface). containerd is the most widely used runtime (it's what Docker uses internally). kubelet talks to containerd over a Unix socket.
>
> **Which package source:** Ubuntu's built-in `containerd` package works but often lags behind upstream by several months. For production, consider installing from the Docker official repo (`apt.dockerproject.org`) to get the latest version.

```bash
# install containerd (Ubuntu repo — sufficient for most setups)
apt-get update
apt-get install -y containerd

# generate default config
mkdir -p /etc/containerd
containerd config default | tee /etc/containerd/config.toml
```

The critical config change: set `SystemdCgroup = true`. Since Ubuntu 22.04 uses systemd as init, both containerd and kubelet must agree to use the systemd cgroup driver — otherwise cgroup management conflicts cause kubelet to crash.

```bash
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

systemctl restart containerd
systemctl enable containerd
```

Verify containerd is running and using the right cgroup driver:
```bash
systemctl status containerd
containerd config dump | grep SystemdCgroup
# should output: SystemdCgroup = true
```

# 3. Install kubeadm, kubelet, kubectl

> **Doc:** [Installing kubeadm, kubelet and kubectl](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/#installing-kubeadm-kubelet-and-kubectl)
>
> **Why these three tools:**
> - `kubelet` — the node agent, runs on every node, manages Pods
> - `kubeadm` — bootstraps the cluster (only needed at setup/upgrade time)
> - `kubectl` — CLI to interact with the cluster
>
> We pin the version with `apt-mark hold` to prevent unintended upgrades — k8s upgrades must be done deliberately, one minor version at a time.

```bash
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gpg

# add the k8s apt signing key (update v1.33 if targeting a different version)
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | \
  gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' | \
  tee /etc/apt/sources.list.d/kubernetes.list

apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl   # prevent auto-upgrades
```

# 4. Initialize the Cluster

> **Doc:** [Creating a cluster with kubeadm](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/)
>
> **What kubeadm init does:** generates all TLS certificates, writes kubeconfig files for each component, and starts the control plane components (etcd, apiserver, controller-manager, scheduler) as **static Pods** — YAML manifests in `/etc/kubernetes/manifests/` that kubelet reads directly, without needing an API server to schedule them.

```bash
kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  --apiserver-advertise-address=<YOUR_SERVER_IP>
```

`--pod-network-cidr=10.244.0.0/16` is Flannel's hardcoded default CIDR. If you use a different CNI or CIDR, change this accordingly.

**What happens during init:**
```
[preflight]      → checks: swap off, ports free, kernel params set, container runtime responding
[certs]          → generates CA + certs for apiserver, etcd, kubelet, front-proxy
[kubeconfig]     → writes /etc/kubernetes/{admin,controller-manager,scheduler,kubelet}.conf
[etcd]           → writes /etc/kubernetes/manifests/etcd.yaml (static Pod)
[control-plane]  → writes manifests for apiserver, controller-manager, scheduler
[kubelet-start]  → starts kubelet; kubelet reads manifests, starts control plane Pods
[addons]         → deploys CoreDNS (cluster DNS) and kube-proxy (Service networking)
```

Save the `kubeadm join` command printed at the end — you'll need it if you add worker nodes later.

## Set up kubeconfig

```bash
mkdir -p $HOME/.kube
cp /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config
```

## Allow scheduling on control-plane node (single-server only)

By default, control plane nodes have a `NoSchedule` taint — user workloads can't land there. On a single-server setup, you need to remove it so your app Pods can run on the same node as the control plane:

```bash
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

Verify the node is Ready:
```bash
kubectl get nodes
# NAME     STATUS     ROLES           AGE   VERSION
# server   NotReady   control-plane   30s   v1.33.x
# (NotReady is expected here — CNI not installed yet, so node network is unready)
```

# 5. Install CNI Plugin (Flannel)

> **Doc:** [Flannel — Kubernetes deployment guide](https://github.com/flannel-io/flannel/blob/master/Documentation/kubernetes.md)
>
> **Why CNI is required:** k8s mandates a flat network where every Pod gets a unique IP and can reach any other Pod without NAT. The kernel doesn't do this out of the box — a CNI plugin sets up the veth pairs, bridges, and routes to make it work. Without CNI, all Pods stay in `Pending` and the node stays `NotReady`.
>
> **Why Flannel:** simplest CNI — uses VXLAN overlay to wrap Pod traffic in UDP, works on any cloud or bare metal without BGP peering. Tradeoff: slight overhead vs Calico/Cilium, fewer features (no NetworkPolicy by default).

```bash
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
```

Flannel runs as a DaemonSet — one Pod per node, manages routes on that node's host network.

Wait for the node to become Ready:
```bash
kubectl get nodes -w
# NAME     STATUS   ROLES           AGE   VERSION
# server   Ready    control-plane   2m    v1.33.x
```

Verify all system Pods are running:
```bash
kubectl get pods -n kube-system
kubectl get pods -n kube-flannel
# etcd, kube-apiserver, kube-controller-manager, kube-scheduler,
# coredns (x2), kube-proxy, kube-flannel-ds should all be Running
```

# 6. Storage: local-path-provisioner

> **Doc:** [rancher/local-path-provisioner](https://github.com/rancher/local-path-provisioner)
>
> **Why:** By default, k8s has no StorageClass — a `PersistentVolumeClaim` will stay `Pending` forever unless a provisioner exists to create the backing volume. For a single server, local-path-provisioner is the simplest option: it dynamically creates a directory on the node's local disk for each PVC. No shared storage, no cloud dependency.
>
> **Tradeoff:** Data is tied to this node. If the node dies, the data is gone. For stateful production workloads (databases), a replicated solution (Longhorn, NFS) is better — but local-path is fine for most single-server use cases.

```bash
# use the versioned URL (v0.0.35), not master branch
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.35/deploy/local-path-storage.yaml

# set as default StorageClass so PVCs bind automatically
kubectl patch storageclass local-path \
  -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

Test it works:
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
# STATUS should be Bound within a few seconds
kubectl delete pvc test-pvc
```

# 7. Ingress Controller (nginx)

> **Doc:** [ingress-nginx — Bare-metal clusters](https://kubernetes.github.io/ingress-nginx/deploy/#bare-metal-clusters)
>
> **Why Ingress:** Services of type `NodePort` work but are ugly (random high port numbers). An Ingress controller sits in front of Services and routes HTTP/HTTPS traffic by hostname and path — so `myapp.example.com` → Service `myapp:80`. On a single server there's no cloud load balancer, so we use the baremetal deployment which exposes the controller via NodePort.

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.15.1/deploy/static/provider/baremetal/deploy.yaml
```

The ingress controller Pod runs with `hostNetwork: false` and is exposed via a NodePort Service. Check the assigned ports:
```bash
kubectl get svc -n ingress-nginx
# ingress-nginx-controller  NodePort  10.96.x.x  80:3XXXX/TCP,443:3XXXX/TCP
```

**Forwarding ports 80/443 to the NodePort** — two options:

Option A: iptables PREROUTING rule (simple, stateless):
```bash
# get the node ports first
HTTP_PORT=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
  -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}')
HTTPS_PORT=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
  -o jsonpath='{.spec.ports[?(@.name=="https")].nodePort}')

iptables -t nat -A PREROUTING -p tcp --dport 80  -j REDIRECT --to-port $HTTP_PORT
iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port $HTTPS_PORT
```

Option B: patch the Service to use `externalIPs` with your server's public IP — traffic to port 80/443 on that IP routes directly to the controller.

# 8. TLS: cert-manager

> **Doc:** [cert-manager — kubectl apply install](https://cert-manager.io/docs/installation/kubectl/)
>
> **Why cert-manager:** Managing TLS certificates manually (renewing every 90 days, deploying Secrets) doesn't scale. cert-manager watches for Ingress/Certificate objects and automatically issues and renews certificates from Let's Encrypt using the ACME protocol. The `http01` solver works by temporarily serving a challenge file via the Ingress controller to prove domain ownership.

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.20.2/cert-manager.yaml

# wait for all three components to be ready before creating issuers
kubectl -n cert-manager rollout status deploy/cert-manager
kubectl -n cert-manager rollout status deploy/cert-manager-webhook
kubectl -n cert-manager rollout status deploy/cert-manager-cainjector
```

Create a ClusterIssuer — tells cert-manager to use Let's Encrypt production and validate via HTTP:

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
          ingressClassName: nginx
```

```bash
kubectl apply -f cluster-issuer.yaml
kubectl get clusterissuer letsencrypt-prod
# READY should be True
```

Now any Ingress annotated with `cert-manager.io/cluster-issuer` gets automatic TLS. cert-manager creates a `Certificate` object, completes the ACME challenge, and stores the cert in the named Secret:

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
    secretName: myapp-tls          # cert-manager creates this Secret
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

# 9. Metrics Server

> **Doc:** [kubernetes-sigs/metrics-server](https://github.com/kubernetes-sigs/metrics-server)
>
> **Why:** The Kubernetes scheduler and HPA (Horizontal Pod Autoscaler) need resource usage data (CPU/memory) to make decisions. The metrics-server scrapes kubelet's `/metrics/resource` endpoint on each node and serves aggregated data via the Kubernetes Metrics API. Without it, `kubectl top`, HPA, and VPA won't work.

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

On a single server with self-signed certs (the default), metrics-server fails to connect to kubelet because TLS verification fails. Patch it to skip kubelet TLS verification:

```bash
kubectl patch deployment metrics-server -n kube-system \
  --type json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```

Verify:
```bash
kubectl top nodes
# NAME     CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%
# server   210m         5%     1800Mi          45%

kubectl top pods -A
```

# Deploy a Test App

Verify the entire stack end-to-end: scheduling → networking → storage → ingress → TLS.

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

# wait for cert to be issued (30-60s)
kubectl get certificate whoami-tls
# READY should be True

curl https://whoami.example.com
```

# Cluster State Summary

After all steps, you should have:

```bash
kubectl get pods -A
# NAMESPACE            NAME                                      READY   STATUS
# cert-manager         cert-manager-xxx                          1/1     Running
# cert-manager         cert-manager-cainjector-xxx               1/1     Running
# cert-manager         cert-manager-webhook-xxx                  1/1     Running
# ingress-nginx        ingress-nginx-controller-xxx              1/1     Running
# kube-flannel         kube-flannel-ds-xxx                       1/1     Running
# kube-system          coredns-xxx (x2)                          1/1     Running
# kube-system          etcd-xxx                                  1/1     Running
# kube-system          kube-apiserver-xxx                        1/1     Running
# kube-system          kube-controller-manager-xxx               1/1     Running
# kube-system          kube-proxy-xxx                            1/1     Running
# kube-system          kube-scheduler-xxx                        1/1     Running
# kube-system          metrics-server-xxx                        1/1     Running
# local-path-storage   local-path-provisioner-xxx                1/1     Running
```

What each namespace contains:
```
kube-system        → core control plane + DNS + kube-proxy
kube-flannel       → CNI DaemonSet (one pod per node)
ingress-nginx      → nginx ingress controller
cert-manager       → TLS automation (3 components: controller, cainjector, webhook)
local-path-storage → dynamic PV provisioner
```

# k3s Alternative (Faster Path)

> **Doc:** [k3s — Quick Start](https://docs.k3s.io/quick-start)
>
> k3s bundles flannel, local-path-provisioner, metrics-server, and traefik ingress into a single binary. The trade-off: less transparency into how components are configured, and traefik instead of nginx (different annotation syntax). Good for a quick production setup; kubeadm is better if you want to learn the internals or plan multi-node expansion.

```bash
curl -sfL https://get.k3s.io | sh -

# kubeconfig
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# k3s already includes: flannel, local-path-provisioner, metrics-server, traefik ingress
# only thing to add on top: cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.20.2/cert-manager.yaml
```

# Upgrades

> **Doc:** [Upgrading kubeadm clusters](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/)
>
> **Rule: never skip minor versions.** k8s only tests and supports sequential upgrades (1.32 → 1.33, not 1.31 → 1.33). The control plane must be upgraded before worker nodes. On a single-server setup, this is the same node.

```bash
# 1. upgrade kubeadm first (it orchestrates the rest)
apt-get install -y kubeadm=1.33.x-*

# 2. check what will change
kubeadm upgrade plan

# 3. apply — upgrades control plane static Pod manifests and CoreDNS/kube-proxy
kubeadm upgrade apply v1.33.x

# 4. upgrade kubelet + kubectl
apt-get install -y kubelet=1.33.x-* kubectl=1.33.x-*
systemctl daemon-reload
systemctl restart kubelet
```

For multi-node clusters, drain each worker node before upgrading it:
```bash
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
# ... upgrade kubelet on the node ...
kubectl uncordon <node>
```

# References

## Official Kubernetes Docs

- [Host preparation (swap, modules, sysctl)](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/#before-you-begin)
- [Container runtimes (containerd, CRI-O)](https://kubernetes.io/docs/setup/production-environment/container-runtimes/)
- [Installing kubeadm / kubelet / kubectl](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/)
- [Creating a cluster with kubeadm](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/)
- [Upgrading kubeadm clusters](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/)
- [Swap memory management (k8s 1.28+)](https://kubernetes.io/docs/concepts/architecture/nodes/#swap-memory)
- [CNI — cluster networking overview](https://kubernetes.io/docs/concepts/cluster-administration/networking/)

## Components

- [Flannel CNI](https://github.com/flannel-io/flannel) — latest
- [local-path-provisioner](https://github.com/rancher/local-path-provisioner) — v0.0.35
- [ingress-nginx — bare-metal](https://kubernetes.github.io/ingress-nginx/deploy/#bare-metal-clusters) — controller-v1.15.1
- [cert-manager](https://cert-manager.io/docs/installation/kubectl/) — v1.20.2
- [metrics-server](https://github.com/kubernetes-sigs/metrics-server) — latest
- [k3s](https://docs.k3s.io/quick-start) — latest
