"""Data ingestion pipeline for GitHub and Kubernetes sources into ChromaDB."""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from backend.sources.kubernetes import KubernetesSource
from backend.vector_store import ChromaVectorStore


class DataIngestionPipeline:
    """Pipeline for ingesting data from GitHub and Kubernetes into vector store."""
    
    def __init__(self, 
                 vector_store: ChromaVectorStore,
                 github_token: Optional[str] = None,
                 kubeconfig_path: Optional[str] = None,
                 k8s_context: Optional[str] = None):
        """Initialize the ingestion pipeline.
        
        Args:
            vector_store: ChromaVectorStore instance
            github_token: GitHub personal access token
            kubeconfig_path: Path to kubeconfig file
            k8s_context: Kubernetes context to use
        """
        self.vector_store = vector_store
        self.github_token = github_token
        self.kubeconfig_path = kubeconfig_path
        self.k8s_context = k8s_context
        
        # Initialize sources
        self.k8s_source = KubernetesSource(
            kubeconfig_path=kubeconfig_path,
            context=k8s_context
        )
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def ingest_kubernetes_data(self, 
                                   namespaces: Optional[List[str]] = None,
                                   resource_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Ingest Kubernetes cluster data into vector store.
        
        Args:
            namespaces: List of namespaces to include (None for all)
            resource_types: List of resource types to include (None for all)
            
        Returns:
            Dictionary with ingestion results
        """
        self.logger.info("Starting Kubernetes data ingestion...")
        start_time = datetime.now()
        
        try:
            entities = []
            
            # Collect all entities
            async for entity in self.k8s_source.generate_entities():
                # Filter by namespace if specified
                if namespaces and hasattr(entity, 'namespace'):
                    if entity.namespace not in namespaces and entity.namespace != 'cluster-wide':
                        continue
                
                # Filter by resource type if specified
                if resource_types and hasattr(entity, 'kind'):
                    if entity.kind not in resource_types:
                        continue
                
                entities.append(entity)
            
            self.logger.info(f"Collected {len(entities)} Kubernetes entities")
            
            # Add entities to vector store in batches
            if entities:
                doc_ids = await self.vector_store.add_entities_batch(entities)
                self.logger.info(f"Added {len(doc_ids)} Kubernetes documents to vector store")
            else:
                doc_ids = []
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "source": "kubernetes",
                "entities_processed": len(entities),
                "documents_added": len(doc_ids),
                "duration_seconds": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"Error during Kubernetes ingestion: {e}")
            return {
                "source": "kubernetes",
                "error": str(e),
                "success": False
            }
    
    async def ingest_github_repo(self, 
                                repo_name: str,
                                branch: Optional[str] = None) -> Dict[str, Any]:
        """Ingest GitHub repository data into vector store.
        
        Note: This is a simplified version. The full GitHub source from sources/github.py
        would need to be adapted to work with our vector store.
        
        Args:
            repo_name: Repository name (format: "owner/repo")
            branch: Branch to sync (None for default branch)
            
        Returns:
            Dictionary with ingestion results
        """
        self.logger.info(f"GitHub ingestion for {repo_name} would be implemented here")
        
        # TODO: Implement GitHub ingestion using the existing github.py source
        # This would require:
        # 1. Adapting the GitHubSource to work with our simplified entity format
        # 2. Converting GitHubCodeFileEntity, GitHubDirectoryEntity, etc. to our format
        # 3. Handling authentication and API calls
        
        return {
            "source": "github",
            "repo_name": repo_name,
            "message": "GitHub ingestion not yet implemented",
            "success": False
        }
    
    async def run_full_ingestion(self, 
                                github_repos: Optional[List[str]] = None,
                                k8s_namespaces: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run full ingestion pipeline for all configured sources.
        
        Args:
            github_repos: List of GitHub repositories to ingest
            k8s_namespaces: List of Kubernetes namespaces to ingest
            
        Returns:
            Dictionary with overall ingestion results
        """
        self.logger.info("Starting full data ingestion pipeline...")
        start_time = datetime.now()
        
        results = {
            "pipeline_start": start_time.isoformat(),
            "sources": {}
        }
        
        # Ingest Kubernetes data
        k8s_result = await self.ingest_kubernetes_data(namespaces=k8s_namespaces)
        results["sources"]["kubernetes"] = k8s_result
        
        # Ingest GitHub data (if repositories specified)
        if github_repos:
            github_results = []
            for repo in github_repos:
                repo_result = await self.ingest_github_repo(repo)
                github_results.append(repo_result)
            results["sources"]["github"] = github_results
        
        end_time = datetime.now()
        results["pipeline_end"] = end_time.isoformat()
        results["total_duration"] = (end_time - start_time).total_seconds()
        
        # Calculate summary statistics
        total_entities = 0
        total_documents = 0
        successful_sources = 0
        
        for source_name, source_result in results["sources"].items():
            if source_name == "github":
                # GitHub returns list of repo results
                for repo_result in source_result:
                    if repo_result.get("success"):
                        successful_sources += 1
                        total_entities += repo_result.get("entities_processed", 0)
                        total_documents += repo_result.get("documents_added", 0)
            else:
                # Other sources return single result
                if source_result.get("success"):
                    successful_sources += 1
                    total_entities += source_result.get("entities_processed", 0)
                    total_documents += source_result.get("documents_added", 0)
        
        results["summary"] = {
            "total_entities_processed": total_entities,
            "total_documents_added": total_documents,
            "successful_sources": successful_sources,
            "vector_store_stats": self.vector_store.get_collection_stats()
        }
        
        self.logger.info(f"Pipeline completed: {total_documents} documents added from {successful_sources} sources")
        
        return results
    
    async def get_cluster_summary(self) -> Dict[str, Any]:
        """Get a summary of the current Kubernetes cluster.
        
        Returns:
            Dictionary with cluster information
        """
        try:
            return await self.k8s_source.get_cluster_summary()
        except Exception as e:
            return {"error": str(e), "success": False}


async def main():
    """Example usage of the ingestion pipeline."""
    # Initialize vector store
    vector_store = ChromaVectorStore(
        persist_directory="./chroma_db",
        collection_name="operius_knowledge"
    )
    
    # Initialize pipeline
    pipeline = DataIngestionPipeline(
        vector_store=vector_store,
        # kubeconfig_path=None,  # Use default kubeconfig
        # k8s_context="kind-operius-demo"  # Use the kind cluster we created
    )
    
    print("=== Kubernetes Cluster Summary ===")
    cluster_summary = await pipeline.get_cluster_summary()
    print(f"Cluster: {cluster_summary}")
    
    print("\n=== Starting Data Ingestion ===")
    results = await pipeline.run_full_ingestion()
    
    print(f"\n=== Ingestion Results ===")
    print(f"Total entities processed: {results['summary']['total_entities_processed']}")
    print(f"Total documents added: {results['summary']['total_documents_added']}")
    print(f"Successful sources: {results['summary']['successful_sources']}")
    
    print(f"\n=== Vector Store Stats ===")
    stats = results['summary']['vector_store_stats']
    print(f"Total documents in store: {stats['total_documents']}")
    print(f"Sources: {stats['sources']}")
    print(f"Kubernetes kinds: {stats['kubernetes_kinds']}")


if __name__ == "__main__":
    asyncio.run(main())
