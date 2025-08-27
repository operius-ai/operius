# Operius
_Our AI agents detect kubernetes failures in real time and immediately tell engineers which code changes or manifests likely caused them._

current functionality:
* data ingestion and search system that connects to github repositories and kubernetes clusters
* stores data in vector database
* _autonomous agents monitoring live k8s clusters and detecting issues_
* _generate static reports_

TODO:
* agent triggers a vector search call on issue detection.
* output showing relevant commits, Dockerfiles, manifests, or previous cluster state.

## tech stack

- **Backend**: Python, AsyncIO
- **Vector Database**: ChromaDB with sentence-transformers (demo-only, move to PostgresQL with pgvector on Azure)
- **Kubernetes**: Python Kubernetes client
- **GitHub**: REST API integration with incremental sync
- **AI**: OpenRouter API gateway for LLM integration

## repo structure

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
