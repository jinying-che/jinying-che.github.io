---
title: "k8s cluster setup on Raspberry Pi"
date: "2026-03-22T09:00:00+08:00"
tags: ["kubernetes", "k8s"]
description: "production-style kubernetes cluster on a single server using kubeadm"
draft: false
---

# Overview

Running a full k8s cluster on a single server — useful for homelab, dev environment, or small-scale production.

This post is split into two parts:

```
┌─────────────────────────────────────────────┐
│              Single Server                  │
│                                             │
│  Part 1 — REQUIRED to have a working cluster│
│  ┌────────────────────────────────────────┐ │
│  │ Control Plane (kubeadm)                │ │
│  │   apiserver, etcd, scheduler, ctrl-mgr │ │
│  │ Worker (same node)                     │ │
│  │   kubelet, kube-proxy, containerd      │ │
│  │ CNI: Flannel                           │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  Part 2 — OPTIONAL application addons       │
│  ┌────────────────────────────────────────┐ │
│  │ Storage:  local-path-provisioner       │ │
│  │ Ingress:  see § Exposing apps          │ │
│  │ TLS:      cert-manager                 │ │
│  │ Metrics:  metrics-server               │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

**Tool choice: kubeadm vs k3s**

| | kubeadm | k3s |
|---|---|---|
| Philosophy | "Real" k8s, full control | Lightweight, batteries-included |
| Binary size | Multiple components | Single binary (~70MB) |
| etcd | Requires separate install | Embedded SQLite or etcd |
| Setup effort | More manual | Much simpler |
| Good for | Learning the internals | Production single-node fast setup |

This guide uses **kubeadm**. For a faster path, see the k3s section at the bottom.

**Minimum requirements:** 2 vCPU, 4GB RAM, 20GB disk, Ubuntu 22.04

# Part 1 — Cluster Setup (Required)

After Part 1 you'll have a fully working k8s cluster — schedulable Pods, Services, DNS. Everything else is optional.

# 1. Install kubeadm, kubelet, kubectl

> **Doc:** [Installing kubeadm, kubelet and kubectl](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/#installing-kubeadm-kubelet-and-kubectl)
>
> **Why these three tools:**
> - `kubelet` — the node agent, runs on every node, manages Pods
> - `kubeadm` — bootstraps the cluster (only needed at setup/upgrade time)
> - `kubectl` — CLI to interact with the cluster

```bash
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gpg

# add the k8s apt signing key — change v1.36 if targeting a different version
# (see § How to check the latest version at the bottom for finding current stable)
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.36/deb/Release.key | \
  sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

# add the kubernetes apt repository — ensure the version (v1.36) matches the key above
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.36/deb/ /' | \
  sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl   # prevent auto-upgrades
```

# 2. The "Fail-Fast" Initialization

Instead of doing chores first, let's try to start the cluster immediately and see why it fails. This is how you learn what k8s actually needs from your OS.

```bash
sudo kubeadm init
```

It will fail with several `[ERROR]` messages. We will address them one by one.

# 3. Solving System Errors (Prepare the Server)

> **Doc:** [kubeadm install — Before you begin](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/#before-you-begin)

Your first set of errors likely looks like this:
*   `[ERROR Swap]: running with swap on is not supported`
*   `[ERROR FileContent--proc-sys-net-bridge-bridge-nf-call-iptables]: ... does not exist`

## Fix: Disable swap

kubelet refuses to start if swap is enabled because it breaks resource guarantees. k8s assumes memory limits are hard — swap allows containers to silently exceed these limits, making OOM decisions unpredictable.

```bash
sudo swapoff -a
sudo sed -i '/swap/d' /etc/fstab

# --- Raspberry Pi Only ---
# The Pi uses a custom service that bypasses /etc/fstab. Disable it:
sudo dphys-swapfile swapoff
sudo dphys-swapfile uninstall
sudo systemctl disable dphys-swapfile
# -------------------------

# Verify swap is disabled
free -h
# Look for "Swap: 0B"
```

## Fix: Load kernel modules & sysctl

`overlay` is needed for overlayfs (container image layers). `br_netfilter` allows iptables to see bridged traffic — required for kube-proxy to intercept Pod-to-Pod packets crossing the bridge.

```bash
# write modules to /etc/modules-load.d/ — systemd-modules-load.service
# reads this dir at boot, so the modules will auto-load on every reboot
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

# load them right now (without reboot) so kubeadm init can proceed
sudo modprobe overlay
sudo modprobe br_netfilter

# set sysctl params to ensure iptables rules apply to bridged traffic 
# and that the node can forward packets between Pods
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system
```

## Fix: Missing Memory Cgroups (Kernel Configuration)

If `kubeadm init` fails with `[ERROR SystemVerification]: missing required cgroups: memory`, your kernel has the memory controller disabled. 

**1. Diagnose:**
Check if the memory controller is enabled (`1` = enabled, `0` = disabled):
```bash
cat /proc/cgroups | grep memory
```

**2. Fix: Add Boot Parameters:**
You need to add `cgroup_enable=memory cgroup_memory=1` to your boot configuration.

*   **Option A: Standard Linux (GRUB)**
    ```bash
    sudo nano /etc/default/grub
    # Append the parameters to the GRUB_CMDLINE_LINUX_DEFAULT line
    # Example: GRUB_CMDLINE_LINUX_DEFAULT="quiet splash cgroup_enable=memory cgroup_memory=1"
    sudo update-grub
    ```

*   **Option B: Raspberry Pi**
    ```bash
    sudo nano /boot/firmware/cmdline.txt
    # Append to the end of the line (stay on a single line):
    # cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1
    ```

**3. Reboot:**
```bash
sudo reboot
```

# 4. Solving the Runtime Error (containerd)

> **Doc:** [Container runtimes — containerd](https://kubernetes.io/docs/setup/production-environment/container-runtimes/#containerd)
>
> **Why:** k8s doesn't run containers directly; it delegates to a container runtime via the CRI (Container Runtime Interface). We use the official Docker repository to get `containerd.io`.

Next error: `[ERROR CRI]: container runtime is not running`.

First, check your OS identity:
```bash
cat /etc/os-release | grep -E '^ID=|^VERSION_CODENAME='
# Example output for Raspberry Pi (Debian 12):
# VERSION_CODENAME=bookworm
# ID=debian
```

Now, add the repository. **Manually update the OS name (debian) and codename (bookworm) in the commands below if your output is different.**

```bash
# 1. Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# 2. Add the repository to Apt sources
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  bookworm stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list

sudo apt-get update
sudo apt-get install -y containerd.io

# Generate modern default config
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml

# CRITICAL: set SystemdCgroup = true. Since Ubuntu/Debian use systemd as init, 
# both containerd and kubelet must agree to use the systemd cgroup driver.
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

sudo systemctl restart containerd
sudo systemctl enable containerd

# Verify containerd is running and using the right cgroup driver
sudo systemctl status containerd
sudo containerd config dump | grep SystemdCgroup
# should output: SystemdCgroup = true
```

# 5. Initialize the Cluster (Success)

> **Doc:** [Creating a cluster with kubeadm](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/)

Now that the OS is prepared and the runtime is healthy, run the initialization for real.

```bash
sudo kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  --apiserver-advertise-address=<YOUR_SERVER_IP>
```

**What kubeadm init does now:** 
*   **[certs]** generates CA + certs for apiserver, etcd, kubelet
*   **[kubeconfig]** writes files for components in `/etc/kubernetes/`
*   **[control-plane]** starts etcd, apiserver, scheduler as **static Pods** (manifests in `/etc/kubernetes/manifests/`)
*   **[addons]** deploys CoreDNS and kube-proxy

## Set up kubeconfig

```bash
mkdir -p $HOME/.kube
sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

## Allow scheduling on control-plane node (single-server only)

By default, control plane nodes have a `NoSchedule` taint. Remove it so your app Pods can run on this single node:

```bash
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

# 6. Install CNI Plugin (Flannel)

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
# server   Ready    control-plane   2m    v1.36.x
```

Verify all system Pods are running:
```bash
kubectl get pods -n kube-system
kubectl get pods -n kube-flannel
# etcd, kube-apiserver, kube-controller-manager, kube-scheduler,
# coredns (x2), kube-proxy, kube-flannel-ds should all be Running
```

# ✅ Cluster is ready

At this point you have a working k8s cluster. You can:
- Deploy Pods, Deployments, StatefulSets, etc.
- Use Services for in-cluster networking
- Reach any Pod via `kubectl port-forward` for testing

Run the test app at the end of this post to verify everything works. If you don't need persistent storage, external HTTP access, automatic TLS, or HPA — **you can stop here.** Part 2 is purely optional addons.

# Part 2 — Optional Addons (Application Platform)

Each addon below is independent — install only what you actually need. Skip what you don't.

# 6. Storage: local-path-provisioner

> **Doc:** [rancher/local-path-provisioner](https://github.com/rancher/local-path-provisioner)
>
> **When to install:** only if your apps use `PersistentVolumeClaim` (databases, file storage, etc.). Without a provisioner, PVCs stay `Pending` forever.
>
> **Why local-path:** simplest option for a single server — dynamically creates a directory on the node's local disk for each PVC. No shared storage, no cloud dependency.
>
> **Tradeoff:** Data is tied to this node. If the node dies, the data is gone. For replicated stateful production workloads, use Longhorn or NFS.

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

# 7. Exposing Apps to the Internet (ingress / Gateway API)

> **When you need this:** only if you want external HTTP/HTTPS traffic routed to your apps by hostname or path (e.g. `myapp.example.com` → Service `myapp:80`). Skip if you only need cluster-internal services or test access via `kubectl port-forward`.

## ⚠️ ingress-nginx is retired (March 2026)

Earlier versions of this post recommended `kubernetes/ingress-nginx`, but **the project was archived on March 24, 2026** — no further releases, bug fixes, or security updates. See the official notice: [Ingress NGINX Retirement: What You Need to Know](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/).

The k8s SIG Network recommends migrating to **Gateway API** (the modern Ingress successor, GA since October 2023). Gateway API is the spec — you still need a controller that implements it.

## Recommended replacements

| Approach | When to use |
|---|---|
| **[Gateway API](https://gateway-api.sigs.k8s.io/) + [Traefik](https://doc.traefik.io/traefik/)** | Future-proof. Traefik is fully conformant with Gateway API v1.5, supports both Gateway API and classic Ingress, lightweight, also bundled in k3s |
| **[Gateway API](https://gateway-api.sigs.k8s.io/) + [NGINX Gateway Fabric](https://github.com/nginx/nginx-gateway-fabric)** | F5/NGINX-maintained — closest spirit successor to ingress-nginx |
| **[Cilium](https://docs.cilium.io/) (CNI + Gateway API)** | Combine networking + ingress in one — would replace Flannel from Part 1 |
| **[Istio](https://istio.io/)** | Full service mesh — only if you need mTLS, traffic shaping, observability |
| **Classic [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/) + Traefik** | Pragmatic stop-gap — same Ingress YAML you may already have, can migrate to Gateway API later |

For the actively-maintained list of conformant Gateway API controllers, see [gateway-api.sigs.k8s.io/implementations/](https://gateway-api.sigs.k8s.io/implementations/).

Detailed installation and YAML for each option is out of scope for this cluster-setup post — see the controller's own docs:

- **Traefik**: [Setup Traefik on Kubernetes](https://doc.traefik.io/traefik/setup/kubernetes/)
- **NGINX Gateway Fabric**: [Quick Start](https://docs.nginx.com/nginx-gateway-fabric/installation/)
- **Cilium**: [Cilium Gateway API](https://docs.cilium.io/en/stable/network/servicemesh/gateway-api/gateway-api/)
- **Gateway API**: [Getting Started Guide](https://gateway-api.sigs.k8s.io/guides/)

# 8. TLS: cert-manager

> **Doc:** [cert-manager — kubectl apply install](https://cert-manager.io/docs/installation/kubectl/)
>
> **When to install:** only if you want automatic TLS certificate issuance and renewal (e.g. from Let's Encrypt). Without external HTTP exposure (§7) you'll need a DNS-01 solver to actually issue certs.

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.20.2/cert-manager.yaml

# wait for all three components to be ready before creating issuers
kubectl -n cert-manager rollout status deploy/cert-manager
kubectl -n cert-manager rollout status deploy/cert-manager-webhook
kubectl -n cert-manager rollout status deploy/cert-manager-cainjector
```

To actually issue certificates, create an `Issuer` or `ClusterIssuer`:

- **HTTP-01 challenge** — needs an ingress controller (see §7 — currently up to you to install). Let's Encrypt sends an HTTP request to your domain; cert-manager serves the challenge response via your ingress.
- **DNS-01 challenge** — needs API credentials for your DNS provider (Cloudflare, Route53, etc.). Works without any ingress controller. See [DNS-01 docs](https://cert-manager.io/docs/configuration/acme/dns01/).

# 9. Metrics Server

> **Doc:** [kubernetes-sigs/metrics-server](https://github.com/kubernetes-sigs/metrics-server)
>
> **When to install:** only if you want `kubectl top`, HPA (Horizontal Pod Autoscaler), or VPA. Without metrics-server, those features simply don't work.

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

On a single server with self-signed kubelet certs (the default), metrics-server fails to connect because TLS verification fails. Patch it to skip kubelet TLS verification:

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

# Verify the Cluster: Test App

Verify scheduling, networking, and DNS work end-to-end. No ingress required — we use `kubectl port-forward` to reach the Service.

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
    targetPort: 80
```

```bash
kubectl apply -f test-app.yaml
kubectl get pods,svc

# wait for both pods to be Running, then test reachability
kubectl port-forward svc/whoami 8080:80 &
curl http://localhost:8080
# should respond with hostname, IP, headers from the whoami container
```

# Cluster State Summary

After Part 1 (cluster only):

```bash
kubectl get pods -A
# NAMESPACE       NAME                              READY   STATUS
# kube-flannel    kube-flannel-ds-xxx               1/1     Running
# kube-system     coredns-xxx (x2)                  1/1     Running
# kube-system     etcd-xxx                          1/1     Running
# kube-system     kube-apiserver-xxx                1/1     Running
# kube-system     kube-controller-manager-xxx       1/1     Running
# kube-system     kube-proxy-xxx                    1/1     Running
# kube-system     kube-scheduler-xxx                1/1     Running
```

After all of Part 2 (storage + cert-manager + metrics-server):

```bash
# additional Pods on top of Part 1:
# cert-manager         cert-manager-xxx                          1/1     Running
# cert-manager         cert-manager-cainjector-xxx               1/1     Running
# cert-manager         cert-manager-webhook-xxx                  1/1     Running
# kube-system          metrics-server-xxx                        1/1     Running
# local-path-storage   local-path-provisioner-xxx                1/1     Running
```

# k3s Alternative (Faster Path)

> **Doc:** [k3s — Quick Start](https://docs.k3s.io/quick-start)
>
> k3s bundles flannel, local-path-provisioner, metrics-server, and Traefik (Ingress + Gateway API capable) into a single binary. The trade-off: less transparency into how components are configured. Good for a quick production setup; kubeadm is better if you want to learn the internals or plan multi-node expansion.

```bash
curl -sfL https://get.k3s.io | sh -

# kubeconfig
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# k3s already includes: flannel, local-path-provisioner, metrics-server, Traefik
# only thing to add on top if you want it: cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.20.2/cert-manager.yaml
```

# Upgrades

> **Doc:** [Upgrading kubeadm clusters](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/)
>
> **Rule: never skip minor versions.** k8s only tests and supports sequential upgrades (1.35 → 1.36, not 1.34 → 1.36). The control plane must be upgraded before worker nodes. On a single-server setup, this is the same node.

```bash
# 1. upgrade kubeadm first (it orchestrates the rest)
apt-get install -y kubeadm=1.36.x-*

# 2. check what will change
kubeadm upgrade plan

# 3. apply — upgrades control plane static Pod manifests and CoreDNS/kube-proxy
kubeadm upgrade apply v1.36.x

# 4. upgrade kubelet + kubectl
apt-get install -y kubelet=1.36.x-* kubectl=1.36.x-*
systemctl daemon-reload
systemctl restart kubelet
```

For multi-node clusters, drain each worker node before upgrading it:
```bash
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
# ... upgrade kubelet on the node ...
kubectl uncordon <node>
```

# How to Check the Latest Version

Versions in this post will drift over time. To find the current stable version of each component:

**Kubernetes (kubeadm, kubelet, kubectl)**
```bash
# latest stable
curl -L -s https://dl.k8s.io/release/stable.txt
# e.g. v1.36.2

# all supported minor versions
curl -L -s https://endoflife.date/api/kubernetes.json | jq '.[0:4]'
```
Or check the [Releases page](https://kubernetes.io/releases/).

**cert-manager**
```bash
curl -s https://api.github.com/repos/cert-manager/cert-manager/releases/latest | grep tag_name
```
Or check [supported releases](https://cert-manager.io/docs/releases/).

**local-path-provisioner**
```bash
curl -s https://api.github.com/repos/rancher/local-path-provisioner/releases/latest | grep tag_name
```

**Flannel** — the post uses `/releases/latest/download/` URL which always tracks the newest release, so no version pin to update.

**metrics-server** — same, uses `/releases/latest/`.

**Generic GitHub pattern** for any project:
```bash
curl -s https://api.github.com/repos/<OWNER>/<REPO>/releases/latest | grep tag_name
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

## Ingress / Gateway API

- [ingress-nginx retirement notice](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)
- [Gateway API (modern Ingress successor)](https://gateway-api.sigs.k8s.io/)
- [Gateway API conformant implementations](https://gateway-api.sigs.k8s.io/implementations/)
- [Ingress controllers list](https://kubernetes.io/docs/concepts/services-networking/ingress-controllers/)
- [Traefik on Kubernetes](https://doc.traefik.io/traefik/setup/kubernetes/)
- [NGINX Gateway Fabric](https://github.com/nginx/nginx-gateway-fabric)
- [Cilium Gateway API](https://docs.cilium.io/en/stable/network/servicemesh/gateway-api/gateway-api/)

## Components Used

- [Flannel CNI](https://github.com/flannel-io/flannel) — latest
- [local-path-provisioner](https://github.com/rancher/local-path-provisioner) — v0.0.35
- [cert-manager](https://cert-manager.io/docs/installation/kubectl/) — v1.20.2
- [metrics-server](https://github.com/kubernetes-sigs/metrics-server) — latest
- [k3s](https://docs.k3s.io/quick-start) — latest
