#!/bin/bash

# Kind Kubernetes Cluster Setup Script
# This script creates a local Kubernetes cluster using Kind

set -e

CLUSTER_NAME="operius-demo"
CONFIG_FILE="kind-config.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Setting up Kind Kubernetes cluster: ${CLUSTER_NAME}${NC}"

# Check if Kind is installed
if ! command -v kind &> /dev/null; then
    echo -e "${RED}❌ Kind is not installed. Please install it first:${NC}"
    echo "  macOS: brew install kind"
    echo "  Linux: curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64 && chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${YELLOW}⚠️  kubectl is not installed. Installing via curl...${NC}"
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
    chmod +x kubectl
    sudo mv kubectl /usr/local/bin/
fi

# Delete existing cluster if it exists
if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo -e "${YELLOW}⚠️  Cluster ${CLUSTER_NAME} already exists. Deleting it...${NC}"
    kind delete cluster --name "${CLUSTER_NAME}"
fi

# Create the cluster
echo -e "${GREEN}📦 Creating Kind cluster with configuration...${NC}"
kind create cluster --name "${CLUSTER_NAME}" --config "${CONFIG_FILE}"

# Wait for cluster to be ready
echo -e "${GREEN}⏳ Waiting for cluster to be ready...${NC}"
kubectl wait --for=condition=Ready nodes --all --timeout=300s

# Display cluster info
echo -e "${GREEN}✅ Cluster created successfully!${NC}"
echo ""
echo -e "${GREEN}📋 Cluster Information:${NC}"
kubectl cluster-info --context "kind-${CLUSTER_NAME}"
echo ""
echo -e "${GREEN}🔍 Nodes:${NC}"
kubectl get nodes
echo ""
echo -e "${GREEN}🎯 To use this cluster:${NC}"
echo "  kubectl config use-context kind-${CLUSTER_NAME}"
echo ""
echo -e "${GREEN}🧹 To delete this cluster:${NC}"
echo "  ./teardown-kind-cluster.sh"
echo "  or: kind delete cluster --name ${CLUSTER_NAME}"
