"""Search agent for querying the vector database with natural language."""

import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.vector_store import ChromaVectorStore


class SearchAgent:
    """Intelligent search agent for querying GitHub and Kubernetes data."""
    
    def __init__(self, vector_store: ChromaVectorStore):
        """Initialize the search agent.
        
        Args:
            vector_store: ChromaVectorStore instance
        """
        self.vector_store = vector_store
        
    async def search(self, 
                    query: str, 
                    max_results: int = 10,
                    source_filter: Optional[str] = None,
                    additional_filters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Perform a semantic search across the knowledge base.
        
        Args:
            query: Natural language search query
            max_results: Maximum number of results to return
            source_filter: Filter by source ('github' or 'kubernetes')
            additional_filters: Additional metadata filters
            
        Returns:
            Dictionary with search results and metadata
        """
        # Prepare filters
        filters = {}
        if source_filter:
            filters['source'] = source_filter
        if additional_filters:
            filters.update(additional_filters)
        
        # Perform search
        results = await self.vector_store.search(
            query=query,
            n_results=max_results,
            filters=filters if filters else None
        )
        
        # Format response
        return {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "total_results": len(results),
            "filters_applied": filters,
            "results": results
        }
    
    async def search_kubernetes(self, 
                               query: str, 
                               resource_kind: Optional[str] = None,
                               namespace: Optional[str] = None,
                               max_results: int = 10) -> Dict[str, Any]:
        """Search specifically in Kubernetes resources.
        
        Args:
            query: Search query
            resource_kind: Filter by Kubernetes resource kind (Pod, Service, etc.)
            namespace: Filter by namespace
            max_results: Maximum results to return
            
        Returns:
            Search results from Kubernetes resources
        """
        # Build filters - ChromaDB requires $and for multiple conditions
        filters = {"source": "kubernetes"}
        
        # Add additional filters using $and operator
        additional_conditions = []
        if resource_kind:
            additional_conditions.append({"kind": resource_kind})
        if namespace:
            additional_conditions.append({"namespace": namespace})
            
        if additional_conditions:
            filters = {"$and": [filters] + additional_conditions}
            
        results = await self.vector_store.search(
            query=query,
            n_results=max_results,
            filters=filters
        )
        
        return {
            "query": query,
            "search_type": "kubernetes",
            "resource_kind": resource_kind,
            "namespace": namespace,
            "total_results": len(results),
            "results": results
        }
    
    async def search_github(self, 
                           query: str,
                           repo_name: Optional[str] = None,
                           language: Optional[str] = None,
                           max_results: int = 10) -> Dict[str, Any]:
        """Search specifically in GitHub resources.
        
        Args:
            query: Search query
            repo_name: Filter by repository name
            language: Filter by programming language
            max_results: Maximum results to return
            
        Returns:
            Search results from GitHub resources
        """
        # Build filters - ChromaDB 1.0.20 uses simple dict format
        filters = {"source": "github"}
        
        if repo_name:
            filters["repo_name"] = repo_name
        if language:
            filters["language"] = language
            
        results = await self.vector_store.search(
            query=query,
            n_results=max_results,
            filters=filters
        )
        
        return {
            "query": query,
            "search_type": "github",
            "repo_name": repo_name,
            "language": language,
            "total_results": len(results),
            "results": results
        }
    
    async def find_related_resources(self, 
                                    entity_id: str,
                                    max_results: int = 5) -> Dict[str, Any]:
        """Find resources related to a specific entity.
        
        Args:
            entity_id: ID of the entity to find related resources for
            max_results: Maximum results to return
            
        Returns:
            Related resources
        """
        # First, try to get the entity content to use as search query
        # This is a simplified approach - in practice you'd want to extract
        # key terms from the entity content
        
        # For now, use the entity_id as a basic search
        results = await self.vector_store.search(
            query=entity_id,
            n_results=max_results
        )
        
        return {
            "entity_id": entity_id,
            "related_resources": results,
            "total_found": len(results)
        }
    
    async def get_cluster_overview(self) -> Dict[str, Any]:
        """Get an overview of all data in the knowledge base.
        
        Returns:
            Overview statistics and sample data
        """
        stats = self.vector_store.get_collection_stats()
        
        # Get some sample results from each source
        samples = {}
        
        if 'kubernetes' in stats.get('sources', {}):
            k8s_samples = await self.vector_store.search_by_source(
                query="kubernetes resources",
                source="kubernetes",
                n_results=3
            )
            samples['kubernetes'] = k8s_samples
        
        if 'github' in stats.get('sources', {}):
            github_samples = await self.vector_store.search_by_source(
                query="code files",
                source="github", 
                n_results=3
            )
            samples['github'] = github_samples
        
        return {
            "overview_timestamp": datetime.now().isoformat(),
            "statistics": stats,
            "sample_data": samples
        }
    
    async def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Analyze the intent of a search query to suggest better search strategies.
        
        Args:
            query: User's search query
            
        Returns:
            Analysis of query intent and suggestions
        """
        query_lower = query.lower()
        
        # Simple keyword-based intent detection
        intent_analysis = {
            "query": query,
            "detected_intents": [],
            "suggested_filters": {},
            "search_suggestions": []
        }
        
        # Detect Kubernetes-related queries
        k8s_keywords = ['pod', 'service', 'deployment', 'namespace', 'ingress', 'configmap', 'secret']
        if any(keyword in query_lower for keyword in k8s_keywords):
            intent_analysis["detected_intents"].append("kubernetes")
            intent_analysis["suggested_filters"]["source"] = "kubernetes"
            
            # Detect specific resource types
            for keyword in k8s_keywords:
                if keyword in query_lower:
                    intent_analysis["suggested_filters"]["kind"] = keyword.capitalize()
                    break
        
        # Detect GitHub-related queries
        github_keywords = ['code', 'file', 'repository', 'repo', 'function', 'class', 'import']
        if any(keyword in query_lower for keyword in github_keywords):
            intent_analysis["detected_intents"].append("github")
            intent_analysis["suggested_filters"]["source"] = "github"
        
        # Detect programming languages
        languages = ['python', 'javascript', 'java', 'go', 'rust', 'typescript', 'yaml', 'json']
        for lang in languages:
            if lang in query_lower:
                intent_analysis["suggested_filters"]["language"] = lang
                break
        
        # Generate search suggestions
        if not intent_analysis["detected_intents"]:
            intent_analysis["search_suggestions"].append("Try adding keywords like 'kubernetes', 'pod', 'code', or 'file'")
        
        if "kubernetes" in intent_analysis["detected_intents"]:
            intent_analysis["search_suggestions"].append("Use search_kubernetes() for better Kubernetes-specific results")
        
        if "github" in intent_analysis["detected_intents"]:
            intent_analysis["search_suggestions"].append("Use search_github() for better code search results")
        
        return intent_analysis
    
    def format_search_results(self, results: List[Dict[str, Any]], show_content: bool = False) -> str:
        """Format search results for display.
        
        Args:
            results: List of search results
            show_content: Whether to include full content in output
            
        Returns:
            Formatted string representation of results
        """
        if not results:
            return "No results found."
        
        formatted = []
        
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            similarity = result['similarity']
            
            # Header with similarity score
            header = f"{i}. [{metadata.get('source', 'unknown').upper()}] {metadata.get('name', 'Unknown')} (similarity: {similarity:.3f})"
            formatted.append(header)
            
            # Add type-specific information
            if metadata.get('source') == 'kubernetes':
                formatted.append(f"   Kind: {metadata.get('kind', 'Unknown')}")
                if metadata.get('namespace') != 'cluster-wide':
                    formatted.append(f"   Namespace: {metadata.get('namespace', 'Unknown')}")
            elif metadata.get('source') == 'github':
                if metadata.get('repo_name'):
                    formatted.append(f"   Repository: {metadata.get('repo_name')}")
                if metadata.get('language'):
                    formatted.append(f"   Language: {metadata.get('language')}")
            
            # Add content preview if requested
            if show_content:
                content = result['document']
                preview = content[:200] + "..." if len(content) > 200 else content
                formatted.append(f"   Content: {preview}")
            
            formatted.append("")  # Empty line between results
        
        return "\n".join(formatted)


async def main():
    """Example usage of the search agent."""
    # Initialize vector store and agent
    vector_store = ChromaVectorStore()
    agent = SearchAgent(vector_store)
    
    print("=== Search Agent Demo ===")
    
    # Get overview
    print("\n1. Knowledge Base Overview:")
    overview = await agent.get_cluster_overview()
    print(f"Total documents: {overview['statistics']['total_documents']}")
    print(f"Sources: {overview['statistics']['sources']}")
    
    # Example searches
    queries = [
        "kubernetes pods running",
        "python code files",
        "nginx configuration",
        "deployment status"
    ]
    
    for query in queries:
        print(f"\n2. Searching for: '{query}'")
        
        # Analyze intent
        intent = await agent.analyze_query_intent(query)
        print(f"Detected intents: {intent['detected_intents']}")
        
        # Perform search
        results = await agent.search(query, max_results=3)
        print(f"Found {results['total_results']} results")
        
        if results['results']:
            formatted = agent.format_search_results(results['results'])
            print(formatted)


if __name__ == "__main__":
    asyncio.run(main())
