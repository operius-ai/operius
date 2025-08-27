# Operius - AI-Powered Knowledge Base for GitHub and Kubernetes

Operius is an intelligent data ingestion and search system that connects to GitHub repositories and Kubernetes clusters, stores the data in a vector database, and provides AI-powered search capabilities.

## 🚀 Features

- **GitHub Integration**: Connect to any GitHub repository and extract code, documentation, and metadata
- **Kubernetes Monitoring**: Extract cluster metadata including pods, services, deployments, and configurations
- **Vector Search**: Semantic search across all ingested data using ChromaDB and sentence transformers
- **AI Agent**: Intelligent search agent with natural language query understanding
- **Local Development**: Complete local setup with Kind Kubernetes clusters

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
