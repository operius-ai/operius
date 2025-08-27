#!/bin/bash

# Kind Kubernetes Cluster Teardown Script
# This script deletes the local Kubernetes cluster created by setup-kind-cluster.sh

set -e

CLUSTER_NAME="operius-demo"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🧹 Tearing down Kind Kubernetes cluster: ${CLUSTER_NAME}${NC}"

# Check if Kind is installed
if ! command -v kind &> /dev/null; then
    echo -e "${RED}❌ Kind is not installed.${NC}"
    exit 1
fi

# Check if cluster exists
if ! kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo -e "${YELLOW}⚠️  Cluster ${CLUSTER_NAME} does not exist.${NC}"
    echo -e "${GREEN}✅ Nothing to clean up.${NC}"
    exit 0
fi

# Delete the cluster
echo -e "${GREEN}🗑️  Deleting Kind cluster...${NC}"
kind delete cluster --name "${CLUSTER_NAME}"

echo -e "${GREEN}✅ Cluster ${CLUSTER_NAME} has been successfully deleted!${NC}"
echo ""
echo -e "${GREEN}📋 Remaining clusters:${NC}"
if kind get clusters 2>/dev/null | grep -q .; then
    kind get clusters
else
    echo "  No Kind clusters remaining"
fi
