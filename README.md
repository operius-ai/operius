# Operius
_Our AI agents detect kubernetes failures in real time and immediately tell engineers which code changes or manifests likely caused them._

current functionality:
data ingestion and search system that connects to github repositories and kubernetes clusters
stores data in vector database
_autonomous agents monitoring live k8s clusters and detecting issues_
_generate static reports_

TODO:
agent triggers a vector search call on issue detection.
output showing relevant commits, Dockerfiles, manifests, or previous cluster state.

## 📁 Project Structure

```
operius/
├── backend/                    # Core backend services
│   ├── sources/               # Data source connectors
│   │   ├── github.py         # GitHub repository connector
│   │   └── kubernetes.py     # Kubernetes cluster connector
│   ├── vector_store.py       # ChromaDB vector database interface
│   ├── search_agent.py       # AI-powered search agent
│   ├── ingestion_pipeline.py # Data ingestion orchestration
│   ├── demo.py              # Complete system demonstration
│   └── test_k8s_connection.py # Kubernetes connectivity test
├── google-adk/               # AI agent core (OpenRouter integration)
├── infra/                    # Infrastructure and deployment
│   ├── demo/                # Kind cluster setup scripts
│   ├── main.tf              # Terraform configuration
│   └── postgres.tf          # PostgreSQL setup
└── tests/                   # Test suite, run with poetry run pytest
```

## 🛠 Technology Stack

- **Backend**: Python, AsyncIO
- **Vector Database**: ChromaDB with sentence-transformers (demo-only, move to PostgresQL with pgvector on Azure)
- **Kubernetes**: Python Kubernetes client
- **GitHub**: REST API integration with incremental sync
- **AI**: OpenRouter API gateway for LLM integration

## 🎯 Quick Start

### 1. Setup and Installation
```bash
# Install dependencies
poetry install

# Set up environment variables
cp .env.example .env
# Add your OPENROUTER_API_KEY and optionally GITHUB_TOKEN
```

### 2. Run the Demo
```bash
# Start with the interactive demo
python -m backend.demo.demo

# This will:
# - Optionally index a GitHub repository
# - Connect to your Kubernetes cluster (minikube)
# - Ingest cluster metadata into the knowledge base
```

### 3. Interactive Chat Interface
```bash
# Launch the chat interface
python -m backend.demo.chat

# Available commands:
# /help - Show available commands
# /stats - Show knowledge base statistics
# /demo - Run search demonstrations
# /history - Show conversation history
# /clear - Clear history
# /quit - Exit
```

## 🔍 Search Demonstrations

The chat interface supports various types of queries:

### Kubernetes Queries
- `"Find all running pods"` - Discover active pods across namespaces
- `"Show me services in kube-system"` - List services in specific namespace
- `"What deployments are available?"` - Find deployment resources
- `"List namespaces"` - Show all cluster namespaces
- `"Show cluster resources"` - General cluster overview

### GitHub Repository Queries
- `"What's in the GitHub repository?"` - Explore repository contents
- `"Show me Python files"` - Find specific file types
- `"How does the vector store work?"` - Understand code functionality
- `"What's the ingestion pipeline?"` - Learn about system components

### Mixed Queries
- `"Show me Kubernetes configs and related code"` - Cross-reference infrastructure and code
- `"Find deployment scripts"` - Locate both K8s manifests and deployment code
- `"What monitoring is set up?"` - Discover observability across both domains

## 🎮 Interactive Features

### `/demo` Command
Run the `/demo` command in the chat interface to see example searches in action:
- Demonstrates different query types
- Shows search intent detection
- Displays formatted results
- Helps you understand what's possible

### Smart Search
- **Intent Detection**: Automatically detects if you're asking about Kubernetes or GitHub
- **Contextual Results**: Returns relevant resources with metadata
- **AI-Powered Responses**: Get natural language explanations (when OpenRouter API key is configured)
- **Fallback Mode**: Works even without AI - returns formatted search results

## 🔧 Adding Data Sources

### GitHub Repositories
```bash
# Use the standalone script
python add_github_repo_simple.py

# Or include in demo flow
python -m backend.demo.demo
# Choose 'y' when prompted about GitHub indexing
```

### Kubernetes Clusters
The system automatically connects to your current kubectl context. Ensure your cluster is accessible:
```bash
# Check cluster access
kubectl cluster-info

# For minikube
minikube status
minikube start  # if not running
```
