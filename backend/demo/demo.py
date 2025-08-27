#!/usr/bin/env python3
"""
Operius Demo Script - Complete system demonstration

This script demonstrates the full pipeline:
1. Optional GitHub repository indexing
2. Connect to Kubernetes cluster (minikube)
3. Ingest K8s metadata into ChromaDB
4. Search the knowledge base with natural language queries
"""

import asyncio
import sys
import os
import base64
from pathlib import Path
from typing import List, Dict, Any
import httpx
from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent))

from backend.vector_store import ChromaVectorStore
from backend.ingestion_pipeline import DataIngestionPipeline
from backend.search_agent import SearchAgent


async def add_github_repository(vector_store, repo_name: str) -> bool:
    """Add a GitHub repository to the knowledge base."""
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        base_url = "https://api.github.com"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "operius-knowledge-base"
        }
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get repository info
            repo_url = f"{base_url}/repos/{repo_name}"
            repo_response = await client.get(repo_url, headers=headers)
            repo_response.raise_for_status()
            repo_data = repo_response.json()
            
            print(f"📁 Repository: {repo_data['full_name']}")
            print(f"📝 Description: {repo_data.get('description', 'No description')}")
            
            # Get default branch and file tree
            default_branch = repo_data.get("default_branch", "main")
            tree_url = f"{base_url}/repos/{repo_name}/git/trees/{default_branch}"
            tree_response = await client.get(tree_url, headers=headers, params={"recursive": "1"})
            tree_response.raise_for_status()
            tree_data = tree_response.json()
            
            # Filter text files
            text_extensions = {'.py', '.js', '.md', '.txt', '.yml', '.yaml', '.json', '.toml'}
            text_files = [
                item for item in tree_data.get("tree", [])
                if item["type"] == "blob" and Path(item["path"]).suffix.lower() in text_extensions
            ]
            
            print(f"🔍 Found {len(text_files)} text files, processing first 20...")
            
            # Process files
            documents_added = 0
            chroma_client = chromadb.PersistentClient(path="./chroma_db")
            collection = chroma_client.get_collection("operius_demo")
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            documents, metadatas, ids = [], [], []
            
            for file_item in text_files[:20]:
                file_path = file_item["path"]
                try:
                    # Get file content
                    file_url = f"{base_url}/repos/{repo_name}/contents/{file_path}"
                    file_response = await client.get(file_url, headers=headers, params={"ref": default_branch})
                    file_response.raise_for_status()
                    file_data = file_response.json()
                    
                    if file_data.get("encoding") == "base64":
                        content = base64.b64decode(file_data["content"]).decode("utf-8", errors="ignore")
                        if content.strip():
                            doc_id = f"github_{repo_name.replace('/', '_')}_{file_path.replace('/', '_')}"
                            document_text = f"File: {file_path}\nRepository: {repo_name}\n\n{content}"
                            
                            metadata = {
                                "source": "github",
                                "repo_name": str(repo_name),
                                "file_path": str(file_path),
                                "file_name": str(Path(file_path).name),
                                "file_extension": str(Path(file_path).suffix),
                                "repo_description": str(repo_data.get('description') or ''),
                                "url": f"https://github.com/{repo_name}/blob/{default_branch}/{file_path}"
                            }
                            
                            documents.append(document_text)
                            metadatas.append(metadata)
                            ids.append(doc_id)
                            documents_added += 1
                            
                except Exception as e:
                    print(f"    ⚠️  Error processing {file_path}: {e}")
                    continue
            
            # Add to ChromaDB
            if documents:
                embeddings = embedding_model.encode(documents).tolist()
                collection.add(documents=documents, metadatas=metadatas, ids=ids, embeddings=embeddings)
                print(f"✅ Successfully added {documents_added} documents from GitHub repository")
                return True
            
    except Exception as e:
        print(f"❌ Error adding GitHub repository: {e}")
        return False
    
    return False


async def main():
    """Run the complete Operius demo."""
    print("Operius Knowledge Base Demo")
    print("=" * 50)
    
    # Step 0: Optional GitHub repository indexing
    print("\n🔧 Step 0: GitHub Repository Indexing (Optional)")
    print("-" * 40)
    
    try:
        add_github = input("Do you want to index a GitHub repository? (y/n): ").strip().lower()
        if add_github in ['y', 'yes']:
            github_url = input("Enter GitHub repository URL or owner/repo: ").strip()
            
            # Parse URL to get owner/repo
            if github_url.startswith("https://github.com/"):
                repo_name = github_url.replace("https://github.com/", "").rstrip("/")
            elif github_url.startswith("github.com/"):
                repo_name = github_url.replace("github.com/", "").rstrip("/")
            else:
                repo_name = github_url
            
            if "/" in repo_name:
                print(f"🎯 Indexing repository: {repo_name}")
                github_token = os.getenv("GITHUB_TOKEN")
                if not github_token:
                    print("⚠️  No GITHUB_TOKEN found. Using unauthenticated requests (rate limited).")
                else:
                    print("✅ GitHub token found - using authenticated requests")
            else:
                print("❌ Invalid repository format. Skipping GitHub indexing.")
                add_github = 'n'
        else:
            print("⏭️  Skipping GitHub repository indexing")
    except KeyboardInterrupt:
        print("\n⏭️  Skipping GitHub repository indexing")
        add_github = 'n'
    
    # Initialize components
    print("\n📦 Step 1: Initializing components...")
    print("-" * 40)
    
    # Vector store
    vector_store = ChromaVectorStore(
        persist_directory="./chroma_db",
        collection_name="operius_demo"
    )
    print("✅ ChromaDB vector store initialized")
    
    # Add GitHub repository if requested
    if add_github in ['y', 'yes'] and "/" in repo_name:
        print("\n📥 Adding GitHub repository to knowledge base...")
        await add_github_repository(vector_store, repo_name)
    
    # Ingestion pipeline
    pipeline = DataIngestionPipeline(
        vector_store=vector_store,
        k8s_context="minikube"  # Use the minikube cluster
    )
    print("✅ Data ingestion pipeline initialized")
    
    # Search agent
    agent = SearchAgent(vector_store)
    print("✅ Search agent initialized")
    
    # Step 2: Get cluster summary
    print("\n🔍 Step 2: Finding Kubernetes clusters...")
    print("-" * 40)
    print("🔍 Searching for Kubernetes clusters...")
    print("📡 Connecting to minikube cluster...")
    
    try:
        cluster_summary = await pipeline.get_cluster_summary()
        if cluster_summary.get("error"):
            print(f"❌ Error connecting to cluster: {cluster_summary['error']}")
            print("💡 Make sure minikube is running: minikube status")
            return
        
        print(f"📊 Cluster: {cluster_summary['cluster_name']}")
        print(f"📈 Resources found:")
        for resource_type, count in cluster_summary.get('resources', {}).items():
            print(f"   • {resource_type}: {count}")
            
    except Exception as e:
        print(f"❌ Failed to connect to Kubernetes: {e}")
        print("💡 Make sure minikube is running and kubectl is configured")
        return
    
    # Step 3: Data ingestion
    print("\n📥 Step 3: Data Ingestion")
    print("-" * 40)
    
    print("🔄 Ingesting Kubernetes metadata...")
    ingestion_results = await pipeline.run_full_ingestion()
    
    k8s_result = ingestion_results['sources']['kubernetes']
    if k8s_result['success']:
        print(f"✅ Successfully ingested {k8s_result['entities_processed']} Kubernetes entities")
        print(f"📝 Added {k8s_result['documents_added']} documents to vector store")
        print(f"⏱️  Ingestion took {k8s_result['duration_seconds']:.2f} seconds")
    else:
        print(f"❌ Ingestion failed: {k8s_result.get('error', 'Unknown error')}")
        return
    
    print("\n🎉 Demo completed successfully!")
    print("\n💡 Next steps:")
    print("   • Use the interactive chat interface: python -m backend.chat")
    print("   • Try /stats to see knowledge base statistics")
    print("   • Ask questions about your Kubernetes cluster and GitHub repositories")
    print("   • Use /help to see available commands")
    

    


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
