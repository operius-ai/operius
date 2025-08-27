# Kind Kubernetes Cluster Demo

This directory contains scripts to quickly spin up and tear down a local Kubernetes cluster using [Kind](https://kind.sigs.k8s.io/).

## Prerequisites

- **Docker**: Must be running
- **Kind**: Install with `brew install kind` (macOS) or follow [installation guide](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- **kubectl**: Will be auto-installed if missing

## Quick Start

### 1. Create Cluster
```bash
cd infra/demo
chmod +x setup-kind-cluster.sh
./setup-kind-cluster.sh
```

### 2. Use Cluster
```bash
kubectl config use-context kind-operius-demo
kubectl get nodes
```

### 3. Clean Up
```bash
./teardown-kind-cluster.sh
```

## Cluster Configuration

The cluster is configured with:
- **Name**: `operius-demo`
- **Nodes**: 1 control-plane + 2 worker nodes
- **Port Mappings**: HTTP (80) and HTTPS (443) forwarded to host
- **Ingress Ready**: Control-plane node labeled for ingress controllers
- **Pod Subnet**: `10.244.0.0/16`
- **Service Subnet**: `10.96.0.0/12`

## Files

- `setup-kind-cluster.sh`: Creates the Kind cluster
- `teardown-kind-cluster.sh`: Deletes the Kind cluster  
- `kind-config.yaml`: Cluster configuration
- `README.md`: This documentation
