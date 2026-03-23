---
title: "kubernetes overview"
date: "2024-11-20T09:38:22+08:00"
tags: ["k8s"]
description: "k8s architecture, key concepts, design philosophy, and learning path"
draft: false
---

# Architecture

Kubernetes has two main parts: the **Control Plane** (brain) and **Worker Nodes** (muscle).

```txt
┌─────────────────────────────────────────────────────────────┐
│                        Control Plane                        │
│                                                             │
│  ┌──────────────┐  ┌──────┐  ┌───────────┐  ┌───────────┐ │
│  │ kube-api-    │  │ etcd │  │ kube-     │  │ kube-     │ │
│  │ server       │  │      │  │ scheduler │  │ controller│ │
│  │              │  │      │  │           │  │ -manager  │ │
│  └──────┬───────┘  └──┬───┘  └─────┬─────┘  └─────┬─────┘ │
│         │             │            │               │       │
│         └─────────────┴────────────┴───────────────┘       │
│                              │                              │
└──────────────────────────────┼──────────────────────────────┘
                               │ (watches & acts via API)
         ┌─────────────────────┼──────────────────────┐
         │                     │                      │
┌────────▼────────┐  ┌─────────▼───────┐  ┌──────────▼──────┐
│   Worker Node 1 │  │  Worker Node 2  │  │  Worker Node 3  │
│                 │  │                 │  │                 │
│  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │
│  │  kubelet  │  │  │  │  kubelet  │  │  │  │  kubelet  │  │
│  ├───────────┤  │  │  ├───────────┤  │  │  ├───────────┤  │
│  │ kube-proxy│  │  │  │ kube-proxy│  │  │  │ kube-proxy│  │
│  ├───────────┤  │  │  ├───────────┤  │  │  ├───────────┤  │
│  │ container │  │  │  │ container │  │  │  │ container │  │
│  │  runtime  │  │  │  │  runtime  │  │  │  │  runtime  │  │
│  ├───────────┤  │  │  ├───────────┤  │  │  ├───────────┤  │
│  │  Pod  Pod │  │  │  │  Pod  Pod │  │  │  │  Pod  Pod │  │
│  └───────────┘  │  │  └───────────┘  │  │  └───────────┘  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Control Plane Components

| Component | Role |
|-----------|------|
| **kube-apiserver** | Single entry point for all operations. Validates requests, persists to etcd, serves the REST API |
| **etcd** | Distributed key-value store. The **source of truth** — all cluster state lives here |
| **kube-scheduler** | Watches for unscheduled Pods, assigns them to a Node based on resources and constraints |
| **kube-controller-manager** | Runs control loops: Node controller, ReplicaSet controller, Endpoint controller, etc. |
| **cloud-controller-manager** | Cloud-specific logic (load balancers, storage, node lifecycle) — only in cloud deployments |

## Worker Node Components

| Component | Role |
|-----------|------|
| **kubelet** | Agent on every node. Ensures containers described in PodSpecs are running and healthy |
| **kube-proxy** | Maintains network rules (iptables/ipvs) to implement Service abstraction |
| **container runtime** | Actually runs containers. k8s talks to it via CRI (e.g. containerd, CRI-O) |

## How They Interact (a request walkthrough)

```
kubectl apply -f deployment.yaml
        │
        ▼
  kube-apiserver       ← authenticates, authorizes, validates
        │
        ▼
      etcd             ← persists desired state
        │
        ▼
  kube-controller-     ← ReplicaSet controller sees 0 pods, creates Pod objects
  manager
        │
        ▼
  kube-scheduler       ← watches unscheduled Pods, picks a Node, binds Pod to Node
        │
        ▼
  kubelet (on node)    ← watches for Pods bound to its node, pulls image, starts container
        │
        ▼
  container runtime    ← runs the actual container
```

---

# Key Concepts

## Workload Resources

```
Deployment                     ← manages rolling updates, rollback
  └── ReplicaSet               ← maintains desired number of Pod replicas
        └── Pod                ← smallest deployable unit (1+ containers sharing network/storage)
              └── Container    ← your actual app process
```

| Resource | Use Case |
|----------|----------|
| **Pod** | Runs one or more tightly-coupled containers |
| **ReplicaSet** | Keeps N replicas of a Pod running (usually managed by Deployment) |
| **Deployment** | Stateless apps — rolling updates, rollback, scaling |
| **StatefulSet** | Stateful apps (databases) — stable network identity, ordered operations |
| **DaemonSet** | Run one Pod per node — log collectors, monitoring agents |
| **Job** | Run to completion — batch tasks |
| **CronJob** | Scheduled Jobs |

## Service & Networking

A **Service** gives a stable IP/DNS to a set of Pods (selected by labels). Pods come and go; Service stays.

| Service Type | Scope | Use Case |
|---|---|---|
| **ClusterIP** | Internal only | Default; Pod-to-Pod communication |
| **NodePort** | External via `NodeIP:Port` | Simple external access, dev/testing |
| **LoadBalancer** | External via cloud LB | Production external traffic (cloud) |
| **ExternalName** | DNS alias | Point to external service by DNS |

**Ingress** = HTTP/HTTPS routing rules (path-based, host-based) sitting in front of Services. Requires an Ingress Controller (e.g. nginx, traefik).

```
Internet → LoadBalancer → Ingress Controller → Ingress rules → Service → Pods
```

## Config & Storage

| Resource | Purpose |
|----------|---------|
| **ConfigMap** | Non-sensitive config — env vars, config files |
| **Secret** | Sensitive data — passwords, tokens (base64 encoded, not encrypted by default) |
| **PersistentVolume (PV)** | A piece of storage provisioned in the cluster |
| **PersistentVolumeClaim (PVC)** | A request for storage by a Pod — binds to a matching PV |
| **StorageClass** | Defines how to dynamically provision PVs |

## Metadata & Organization

- **Namespace** — virtual cluster within a cluster, isolates resources by team/env
- **Label** — key-value pairs on resources (`app: nginx`, `env: prod`)
- **Selector** — query labels to target resources (`app: nginx`)
- **Annotation** — non-identifying metadata (deployment tools, git SHA, etc.)

## Security

| Resource | Purpose |
|----------|---------|
| **ServiceAccount** | Identity for a Pod to authenticate with the API server |
| **Role / ClusterRole** | Defines permissions (verbs on resources) |
| **RoleBinding / ClusterRoleBinding** | Grants a Role to a ServiceAccount/User |

---

# Key Design & Philosophy

## 1. Declarative, Not Imperative

You describe **what you want** (desired state), not **how to get there**.

```yaml
# declarative: "I want 3 nginx pods"
spec:
  replicas: 3

# vs imperative: "start 3 nginx pods right now"
kubectl run nginx-1 ...
kubectl run nginx-2 ...
kubectl run nginx-3 ...
```

k8s continuously works to make **actual state = desired state**.

## 2. Control Loop (Reconciliation)

Every controller runs an infinite loop:

```
loop:
  desired = read desired state from etcd
  actual  = observe real world
  if desired != actual:
      take action to converge
```

This is why k8s is **self-healing** — if a Pod dies, the controller notices and creates a new one.

## 3. Everything is an API Resource

k8s is fundamentally an API. Every object (Pod, Service, Deployment) is a REST resource. This makes it:
- Extensible via **CustomResourceDefinitions (CRD)** — define your own resource types
- Automatable — everything `kubectl` does, you can do via API

## 4. Loose Coupling via Labels & Selectors

Components don't reference each other by name. A Service doesn't know which specific Pods it routes to — it selects by labels.

```
Service  ──(selector: app=nginx)──► Pod (label: app=nginx)
                                    Pod (label: app=nginx)
                                    Pod (label: app=nginx)
```

Add/remove Pods freely — the Service automatically updates its endpoint list.

## 5. Immutable Infrastructure

Don't patch a running Pod. Replace it with a new one.

```
Update nginx 1.24 → 1.25:
  NOT: exec into pod, upgrade binary
  YES: update image in Deployment → k8s rolls out new Pods, terminates old ones
```

## 6. Single Responsibility

Each component does one thing: scheduler only schedules, kubelet only manages local pods, etc. This composability allows swapping components (e.g. different schedulers, CNI plugins).

---

# Fundamentals

## Linux Primitives Under the Hood

Every k8s abstraction maps to a Linux kernel feature. Understanding this makes k8s behavior much less magical.

### Linux Namespaces → Pod Isolation

A **namespace** partitions a global kernel resource so each process sees its own isolated view. When k8s creates a Pod, the container runtime creates a set of namespaces for it:

```
k8s concept          Linux namespace     what it isolates
─────────────────────────────────────────────────────────
Pod network stack  → net namespace    → network interfaces, iptables, routing table
Pod processes      → pid namespace    → process tree (PID 1 inside container ≠ host PID 1)
Pod filesystem     → mnt namespace    → mount points, /proc, /sys
Pod hostname       → uts namespace    → hostname, domainname
Pod IPC            → ipc namespace    → shared memory, semaphores, message queues
```

Two containers in the **same Pod** share the `net` and `ipc` namespaces — that's why they can talk via `localhost` and share memory. Each container gets its own `mnt` namespace.

```
Pod
├── net namespace (shared by all containers in pod)  ← "localhost" works across containers
├── ipc namespace (shared)
└── Container A              Container B
    └── mnt namespace (own)  └── mnt namespace (own)
    └── pid namespace (own)  └── pid namespace (own)
```

Verify on the host:
```bash
# find the PID of a container process on the host
crictl inspect <container-id> | grep pid

# see its namespaces
ls -la /proc/<pid>/ns/
# net -> net:[4026531992]   ← same net ns as other containers in the pod
# mnt -> mnt:[4026532xxx]   ← unique per container
```

### cgroups → resource.requests/limits

**cgroups (control groups)** limit and account for resource usage. When you set `resources` in a Pod spec, kubelet translates them to cgroup config:

```
k8s spec                            cgroup controller
────────────────────────────────────────────────────────────────
resources.requests.cpu: "500m"   → cpu.shares (proportional weight, soft limit)
resources.limits.cpu: "1"        → cpu.cfs_quota_us / cpu.cfs_period_us (hard cap)
resources.requests.memory: "256Mi" → (used for scheduling math only)
resources.limits.memory: "512Mi" → memory.limit_in_bytes (OOM-killer threshold)
```

cgroup hierarchy on the node:
```
/sys/fs/cgroup/
└── kubepods/
    ├── besteffort/          ← Pods with no requests/limits (QoS: BestEffort)
    ├── burstable/           ← Pods with requests < limits  (QoS: Burstable)
    │   └── pod<uid>/
    │       └── <container>/
    │           ├── cpu.cfs_quota_us
    │           └── memory.limit_in_bytes
    └── guaranteed/          ← Pods where requests == limits (QoS: Guaranteed)
```

QoS class matters: when node is under memory pressure, `BestEffort` pods are OOM-killed first, then `Burstable`, never `Guaranteed`.

### veth pairs + bridge → Pod networking

Each Pod gets its own network namespace with a virtual ethernet interface. The CNI plugin wires it to the host:

```
Pod network namespace          Host network namespace
┌──────────────────┐          ┌────────────────────────────┐
│  eth0 (Pod IP)   │          │  cni0 (bridge, 10.244.1.1) │
│  10.244.1.5      │          │                            │
└────────┬─────────┘          │  veth3f2a  veth8b1c  ...  │
         │                    └──────┬──────────┬──────────┘
         └──── veth pair ────────────┘          │
              (one end in pod ns,          other pods
               other end on host bridge)
```

Step by step when a Pod is created:
```
1. kubelet asks container runtime to create a "pause" container
   └── pause container creates the pod's net/ipc namespaces (and holds them alive)

2. CNI plugin runs:
   a. create veth pair (vethXXX ↔ eth0)
   b. move eth0 into pod's net namespace
   c. assign Pod IP to eth0
   d. attach vethXXX to bridge (cni0)
   e. add routes so pod can reach other pods

3. App containers join the pause container's net namespace
   └── they all share eth0 and the Pod IP
```

The **pause container** is the invisible container you never write — its only job is to hold namespaces so app containers can restart without losing the Pod's IP.

### overlayfs → container image layers

Container images are stacked read-only layers. overlayfs merges them into one coherent filesystem:

```
Image layers (read-only):
  layer 3: app binary          /app/server
  layer 2: python runtime      /usr/lib/python3/...
  layer 1: ubuntu base         /bin, /lib, /etc, ...

overlayfs mounts:
  upperdir (read-write)  ← container's writable layer (lost on container death)
  lowerdir (read-only)   ← merged image layers
  merged   (view)        ← what the container sees at /

Write (copy-on-write): first write to a file copies it from lowerdir to upperdir,
then modifies the copy. Original layer untouched.
```

This is why:
- Multiple containers sharing the same image use almost no extra disk — they share lowerdir
- Container writes are ephemeral — upperdir is deleted when container dies
- PersistentVolumes mount into the container bypassing overlayfs entirely

### iptables → Service (ClusterIP)

kube-proxy programs iptables rules to implement Service load balancing. When you create a Service:

```
Service: ClusterIP 10.96.0.10:80 → Pods [10.244.1.5, 10.244.2.3]

iptables rules kube-proxy writes:
─────────────────────────────────────────────────────────────────
PREROUTING/OUTPUT chain
  → match dst 10.96.0.10:80 → jump KUBE-SVC-XXXXX

KUBE-SVC-XXXXX chain (load balancing)
  → 50% probability → jump KUBE-SEP-AAA    (endpoint 10.244.1.5:8080)
  → 50% probability → jump KUBE-SEP-BBB    (endpoint 10.244.2.3:8080)

KUBE-SEP-AAA chain
  → DNAT dst to 10.244.1.5:8080           (replace VIP with real Pod IP)
```

Dry run — packet flow for a ClusterIP request:
```
Client Pod sends packet: src=10.244.3.2, dst=10.96.0.10:80
         │
         ▼ iptables PREROUTING
         matches KUBE-SVC → random select endpoint → DNAT
         │
         ▼ packet now: src=10.244.3.2, dst=10.244.1.5:8080
         │
         ▼ routed via CNI to destination Pod
         │
         ▼ reply: src=10.244.1.5:8080, dst=10.244.3.2
           (conntrack reverses the DNAT automatically)
```

IPVS mode (alternative to iptables): same concept but uses kernel's virtual server table — O(1) lookup vs O(n) iptables chains, better for clusters with thousands of Services.

### Summary: k8s abstraction → Linux primitive

```
k8s concept              Linux primitive        kernel subsystem
────────────────────────────────────────────────────────────────
Pod isolation          → namespaces           → kernel/nsproxy.c
resource limits        → cgroups v2           → kernel/cgroup/
Pod networking         → veth + bridge        → drivers/net/veth.c
image filesystem       → overlayfs            → fs/overlayfs/
Service load balancing → iptables / IPVS      → netfilter / net/netfilter/
container security     → seccomp + capabilities → kernel/seccomp.c
```

---

## Pod Lifecycle

```
Pending → Running → Succeeded (Job done)
                 → Failed    (container exited with error)
                 → Unknown   (node lost)

Within Running:
  container state: Waiting | Running | Terminated
```

Probes that kubelet runs:
- **livenessProbe** — is the app alive? Restart container if it fails
- **readinessProbe** — is the app ready to serve traffic? Remove from Service endpoints if it fails
- **startupProbe** — has the app finished starting? (for slow-starting apps)

## Scheduling

The scheduler picks a Node for each new Pod in two phases:

```
1. Filter (Predicates)    — which nodes CAN run this pod?
   - enough CPU/memory?
   - correct nodeSelector/affinity?
   - taints/tolerations?

2. Score (Priorities)     — which node is BEST?
   - most free resources?
   - spread across zones?

→ Highest score wins, Pod gets bound to that Node
```

Key scheduling controls:

| Mechanism | Purpose |
|-----------|---------|
| `resources.requests/limits` | Reserve and cap CPU/memory per container |
| `nodeSelector` | Pin Pod to nodes with specific labels |
| `affinity/antiAffinity` | Soft/hard rules for co-location or spreading |
| `taints & tolerations` | Mark nodes as special (GPU, infra); Pods must tolerate to land there |

## Networking Model

k8s mandates a **flat network**:
- Every Pod gets its own IP
- Any Pod can reach any other Pod directly (no NAT)
- Implemented by a CNI plugin (Flannel, Calico, Cilium, etc.)

```
Pod A (10.244.1.5) ──── CNI ──── Pod B (10.244.2.8)
  no NAT, direct routing
```

Service networking (how ClusterIP works):
```
Client Pod → Service ClusterIP:Port
                    │
              kube-proxy iptables/ipvs rules
                    │
              Pod endpoint (round-robin)
```

## Rolling Updates

```
Deployment: replicas=3, image: nginx:1.24 → nginx:1.25

Step 1: create 1 new Pod (nginx:1.25)         [old=3, new=1]
Step 2: wait for new Pod ready
Step 3: terminate 1 old Pod                   [old=2, new=1]
Step 4: repeat until all replaced             [old=0, new=3]

maxSurge:       how many extra Pods above desired (default 25%)
maxUnavailable: how many Pods can be down at once (default 25%)
```

Rollback is instant — Deployment keeps previous ReplicaSet around:
```
kubectl rollout undo deployment/nginx
```

---

# Learning Path

```
Stage 1 — Concepts (this post)
  ✓ Architecture
  ✓ Key objects: Pod, Deployment, Service, ConfigMap, PVC
  ✓ Design philosophy: declarative, control loops, labels

Stage 2 — Hands-on Basics
  → kubectl: get, describe, logs, exec, apply, delete
  → Write YAML: Deployment + Service + ConfigMap
  → Understand: rolling updates, scaling, namespaces
  → Setup: minikube or kind for local dev

Stage 3 — Networking Deep Dive
  → How Services work (iptables/ipvs)
  → CNI plugins (Flannel vs Calico vs Cilium)
  → Ingress + cert-manager + TLS
  → NetworkPolicy (pod-level firewall)
  → See: k8s/service_discovery post

Stage 4 — Storage
  → PV / PVC / StorageClass
  → StatefulSets for databases
  → CSI drivers

Stage 5 — Production Concerns
  → RBAC, NetworkPolicy, Pod Security
  → Resource requests/limits, LimitRange, ResourceQuota
  → HPA (Horizontal Pod Autoscaler)
  → Health probes, PodDisruptionBudget
  → Cluster setup: see k8s/cluster_setup post

Stage 6 — Ecosystem
  → Helm (package manager) — see k8s/helm post
  → Operators & CRDs
  → GitOps (ArgoCD / Flux)
  → Service Mesh (Istio / Linkerd)
```
