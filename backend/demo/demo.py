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


async def main():
    """Run the complete Operius demo."""
    print("Operius Knowledge Base Demo")
    print("=" * 50)
    
    # Initialize components
    print("\n📦 Initializing components...")
    
    # Vector store
    vector_store = ChromaVectorStore(
        persist_directory="./chroma_db",
        collection_name="operius_demo"
    )
    print("✅ ChromaDB vector store initialized")
    
    # Ingestion pipeline
    pipeline = DataIngestionPipeline(
        vector_store=vector_store,
        k8s_context="minikube"  # Use the minikube cluster
    )
    print("✅ Data ingestion pipeline initialized")
    
    # Search agent
    agent = SearchAgent(vector_store)
    print("✅ Search agent initialized")
    
    # Step 1: Get cluster summary
    print("\n🔍 Step 1: Kubernetes Cluster Analysis")
    print("-" * 40)
    
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
    
    # Step 2: Data ingestion
    print("\n📥 Step 2: Data Ingestion")
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
    
    # Step 3: Vector store statistics
    print("\n📊 Step 3: Knowledge Base Statistics")
    print("-" * 40)
    
    stats = vector_store.get_collection_stats()
    print(f"📚 Total documents: {stats['total_documents']}")
    print(f"🔍 Embedding model: {stats['embedding_model']}")
    print(f"📂 Data sources: {list(stats['sources'].keys())}")
    
    if stats['kubernetes_kinds']:
        print(f"☸️  Kubernetes resource types:")
        for kind, count in stats['kubernetes_kinds'].items():
            print(f"   • {kind}: {count}")
    
    # Step 4: Interactive search demo
    print("\n🔎 Step 4: Search Demonstrations")
    print("-" * 40)
    
    # Demo queries
    demo_queries = [
        ("Find all running pods", "kubernetes"),
        ("Show me services", "kubernetes"), 
        ("What deployments are available?", "kubernetes"),
        ("List namespaces", "kubernetes"),
        ("Show cluster resources", None)
    ]
    
    for query, source_filter in demo_queries:
        print(f"\n🔍 Query: '{query}'")
        
        # Analyze intent
        intent = await agent.analyze_query_intent(query)
        if intent['detected_intents']:
            print(f"🧠 Detected intent: {', '.join(intent['detected_intents'])}")
        
        # Perform search
        if source_filter:
            results = await agent.search_kubernetes(query, max_results=3)
        else:
            results = await agent.search(query, max_results=3)
        
        if results['total_results'] > 0:
            print(f"📋 Found {results['total_results']} results:")
            formatted = agent.format_search_results(results['results'][:2])  # Show top 2
            print(formatted)
        else:
            print("📭 No results found")
    
    # Step 5: Knowledge base overview
    print("\n📈 Step 5: Knowledge Base Overview")
    print("-" * 40)
    
    overview = await agent.get_cluster_overview()
    print(f"🕐 Overview generated at: {overview['overview_timestamp']}")
    
    if overview['sample_data'].get('kubernetes'):
        print(f"🔍 Sample Kubernetes resources:")
        for i, sample in enumerate(overview['sample_data']['kubernetes'][:2], 1):
            metadata = sample['metadata']
            print(f"   {i}. {metadata.get('kind', 'Unknown')} '{metadata.get('name', 'Unknown')}' "
                  f"in {metadata.get('namespace', 'default')}")
    
    print("\n🎉 Demo completed successfully!")
    print("\n💡 Next steps:")
    print("   • Add GitHub repositories to the knowledge base")
    print("   • Integrate with the google-adk agent for AI-powered responses")
    print("   • Build a web interface for easier interaction")
    print("   • Set up automated ingestion pipelines")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
