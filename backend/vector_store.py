"""Vector store implementation using ChromaDB for storing and searching embeddings."""

import asyncio
import uuid
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


class ChromaVectorStore:
    """ChromaDB-based vector store for storing and searching document embeddings."""
    
    def __init__(self, 
                 persist_directory: str = "./chroma_db",
                 collection_name: str = "operius_knowledge",
                 embedding_model: str = "all-MiniLM-L6-v2"):
        """Initialize ChromaDB vector store.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection to store documents
            embedding_model: SentenceTransformer model name for embeddings
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Operius knowledge base with GitHub and Kubernetes data"}
        )
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using SentenceTransformer.
        
        Args:
            text: Text to embed
            
        Returns:
            List of float values representing the embedding
        """
        embedding = self.embedding_model.encode(text)
        return embedding.tolist()
    
    def _prepare_document_text(self, entity: Any) -> str:
        """Prepare text content from entity for embedding.
        
        Args:
            entity: GitHub or Kubernetes entity
            
        Returns:
            Formatted text for embedding
        """
        text_parts = []
        
        # Add entity type and name
        if hasattr(entity, 'kind'):
            text_parts.append(f"Type: {entity.kind}")
        elif hasattr(entity, 'source_name'):
            text_parts.append(f"Source: {entity.source_name}")
            
        if hasattr(entity, 'name'):
            text_parts.append(f"Name: {entity.name}")
            
        # Add namespace for K8s resources
        if hasattr(entity, 'namespace') and entity.namespace:
            text_parts.append(f"Namespace: {entity.namespace}")
            
        # Add repository info for GitHub resources
        if hasattr(entity, 'repo_name') and entity.repo_name:
            text_parts.append(f"Repository: {entity.repo_name}")
        if hasattr(entity, 'repo_owner') and entity.repo_owner:
            text_parts.append(f"Owner: {entity.repo_owner}")
            
        # Add path for files
        if hasattr(entity, 'path') and entity.path:
            text_parts.append(f"Path: {entity.path}")
            
        # Add language for code files
        if hasattr(entity, 'language') and entity.language:
            text_parts.append(f"Language: {entity.language}")
            
        # Add labels for K8s resources
        if hasattr(entity, 'labels') and entity.labels:
            labels_text = ", ".join([f"{k}={v}" for k, v in entity.labels.items()])
            text_parts.append(f"Labels: {labels_text}")
            
        # Add main content
        if hasattr(entity, 'content') and entity.content:
            # Truncate very long content
            content = entity.content[:2000] + "..." if len(entity.content) > 2000 else entity.content
            text_parts.append(f"Content: {content}")
            
        return "\n".join(text_parts)
    
    def _extract_metadata(self, entity: Any) -> Dict[str, Any]:
        """Extract metadata from entity for filtering.
        
        Args:
            entity: GitHub or Kubernetes entity
            
        Returns:
            Dictionary of metadata
        """
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "entity_id": getattr(entity, 'entity_id', str(uuid.uuid4())),
            "source": getattr(entity, 'source_name', 'unknown'),
        }
        
        # Add entity-specific metadata
        if hasattr(entity, 'kind'):
            metadata['kind'] = entity.kind
            metadata['type'] = 'kubernetes'
        elif hasattr(entity, 'source_name') and entity.source_name == 'github':
            metadata['type'] = 'github'
            
        if hasattr(entity, 'namespace'):
            metadata['namespace'] = entity.namespace
            
        if hasattr(entity, 'repo_name'):
            metadata['repo_name'] = entity.repo_name
            
        if hasattr(entity, 'repo_owner'):
            metadata['repo_owner'] = entity.repo_owner
            
        if hasattr(entity, 'language'):
            metadata['language'] = entity.language
            
        if hasattr(entity, 'name'):
            metadata['name'] = entity.name
            
        # Convert all values to strings (ChromaDB requirement)
        return {k: str(v) for k, v in metadata.items()}
    
    async def add_entity(self, entity: Any) -> str:
        """Add a single entity to the vector store.
        
        Args:
            entity: GitHub or Kubernetes entity to add
            
        Returns:
            Document ID
        """
        # Prepare text and metadata
        text = self._prepare_document_text(entity)
        metadata = self._extract_metadata(entity)
        
        # Generate embedding
        embedding = self._generate_embedding(text)
        
        # Generate document ID
        doc_id = f"{metadata['source']}_{metadata['entity_id']}_{uuid.uuid4().hex[:8]}"
        
        # Add to collection
        self.collection.add(
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[doc_id]
        )
        
        return doc_id
    
    async def add_entities_batch(self, entities: List[Any], batch_size: int = 100) -> List[str]:
        """Add multiple entities to the vector store in batches.
        
        Args:
            entities: List of entities to add
            batch_size: Number of entities to process in each batch
            
        Returns:
            List of document IDs
        """
        doc_ids = []
        
        for i in range(0, len(entities), batch_size):
            batch = entities[i:i + batch_size]
            
            texts = []
            embeddings = []
            metadatas = []
            batch_ids = []
            
            for entity in batch:
                text = self._prepare_document_text(entity)
                metadata = self._extract_metadata(entity)
                embedding = self._generate_embedding(text)
                doc_id = f"{metadata['source']}_{metadata['entity_id']}_{uuid.uuid4().hex[:8]}"
                
                texts.append(text)
                embeddings.append(embedding)
                metadatas.append(metadata)
                batch_ids.append(doc_id)
            
            # Add batch to collection
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=batch_ids
            )
            
            doc_ids.extend(batch_ids)
            print(f"Added batch {i//batch_size + 1}: {len(batch)} entities")
        
        return doc_ids
    
    async def search(self, 
                    query: str, 
                    n_results: int = 10,
                    filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar documents in the vector store.
        
        Args:
            query: Search query text
            n_results: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of search results with documents, metadata, and distances
        """
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # Prepare where clause for filtering
        where_clause = None
        if filters:
            where_clause = filters
        
        # Search in collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i],
                'similarity': 1 - results['distances'][0][i]  # Convert distance to similarity
            })
        
        return formatted_results
    
    async def search_by_source(self, 
                              query: str, 
                              source: str,
                              n_results: int = 10) -> List[Dict[str, Any]]:
        """Search for documents from a specific source.
        
        Args:
            query: Search query text
            source: Source to filter by ('github' or 'kubernetes')
            n_results: Number of results to return
            
        Returns:
            List of search results
        """
        return await self.search(
            query=query,
            n_results=n_results,
            filters={"source": source}
        )
    
    async def search_kubernetes_by_kind(self, 
                                       query: str, 
                                       kind: str,
                                       n_results: int = 10) -> List[Dict[str, Any]]:
        """Search for Kubernetes resources by kind.
        
        Args:
            query: Search query text
            kind: Kubernetes resource kind (Pod, Service, etc.)
            n_results: Number of results to return
            
        Returns:
            List of search results
        """
        return await self.search(
            query=query,
            n_results=n_results,
            filters={"kind": kind}
        )
    
    async def search_github_by_repo(self, 
                                   query: str, 
                                   repo_name: str,
                                   n_results: int = 10) -> List[Dict[str, Any]]:
        """Search for GitHub resources by repository.
        
        Args:
            query: Search query text
            repo_name: Repository name to filter by
            n_results: Number of results to return
            
        Returns:
            List of search results
        """
        return await self.search(
            query=query,
            n_results=n_results,
            filters={"repo_name": repo_name}
        )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection.
        
        Returns:
            Dictionary with collection statistics
        """
        count = self.collection.count()
        
        # Get sample of metadata to understand data distribution
        sample_results = self.collection.get(limit=min(100, count))
        
        sources = {}
        kinds = {}
        repos = {}
        
        if sample_results['metadatas']:
            for metadata in sample_results['metadatas']:
                source = metadata.get('source', 'unknown')
                sources[source] = sources.get(source, 0) + 1
                
                if metadata.get('kind'):
                    kind = metadata['kind']
                    kinds[kind] = kinds.get(kind, 0) + 1
                    
                if metadata.get('repo_name'):
                    repo = metadata['repo_name']
                    repos[repo] = repos.get(repo, 0) + 1
        
        return {
            "total_documents": count,
            "sources": sources,
            "kubernetes_kinds": kinds,
            "github_repos": repos,
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_model_name
        }
    
    def reset_collection(self):
        """Reset the collection (delete all documents)."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Operius knowledge base with GitHub and Kubernetes data"}
        )
