


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


### Phase 1: Analysis and Architecture
- [x] Analyze backend/ directory structure and existing code
- [x] Analyze google-adk/ directory structure  
- [x] Review existing GitHub connector in backend/sources/github.py

### Phase 2: Core Components
- [x] Create Kubernetes metadata connector
- [x] Set up local Chroma vector database
- [x] Create data ingestion pipeline for GitHub and K8s data
- [x] Build search agent for vector database

### Phase 3: Integration and Demo
- [x] Create main demo script to test the complete system
- [x] Create requirements.txt for the project
- [x] Install dependencies and test the system

## 🎯 Current Tasks

- [x] Update README.md with project overview and todo list from last run
- [ ] Replace requirements.txt with pyproject.toml and Poetry configuration
- [ ] Create tests/ directory with relevant tests for the new code
- [ ] Test vector store functionality
- [ ] Test Kubernetes source connector
- [ ] Test search agent functionality
- [ ] Test ingestion pipeline

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Docker Desktop
- kubectl
- Kind (for local Kubernetes)

### 1. Set up Local Kubernetes Cluster

```bash
cd infra/demo
./setup-kind-cluster.sh
```

### 2. Install Dependencies

Using Poetry (recommended):
```bash
poetry install
poetry shell
```

Or using pip:
```bash
cd backend
pip install -r requirements.txt
```

### 3. Test Kubernetes Connection

```bash
python test_k8s_connection.py
```

### 4. Run Full Demo

```bash
python demo.py
```

## 🔍 Usage Examples

### Search Kubernetes Resources
```python
from search_agent import SearchAgent
from vector_store import ChromaVectorStore

vector_store = ChromaVectorStore()
agent = SearchAgent(vector_store)

# Search for pods
results = await agent.search_kubernetes("running pods", max_results=5)

# Search by resource type
results = await agent.search_kubernetes("nginx", resource_kind="Deployment")
```

### Ingest Data
```python
from ingestion_pipeline import DataIngestionPipeline

pipeline = DataIngestionPipeline(vector_store)

# Ingest Kubernetes data
results = await pipeline.ingest_kubernetes_data()

# Ingest GitHub repository (future feature)
results = await pipeline.ingest_github_repo("owner/repo")
```

## 🧪 Testing

Run the test suite:
```bash
pytest tests/
```

## 📈 Next Steps

1. **GitHub Integration**: Complete GitHub repository ingestion using existing connector
2. **Web Interface**: Build FastAPI web interface for easier interaction  
3. **AI Enhancement**: Integrate with google-adk agent for AI-powered responses
4. **Monitoring**: Add metrics and observability
5. **Production**: Deploy to cloud infrastructure
