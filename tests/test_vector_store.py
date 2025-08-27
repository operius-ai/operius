"""Tests for the ChromaDB vector store implementation."""

import pytest
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock
from pathlib import Path

from backend.vector_store import ChromaVectorStore


@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for test database."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def vector_store(temp_db_dir):
    """Create a test vector store instance."""
    return ChromaVectorStore(
        persist_directory=temp_db_dir,
        collection_name="test_collection",
        embedding_model="all-MiniLM-L6-v2"
    )


@pytest.fixture
def mock_k8s_entity():
    """Create a mock Kubernetes entity for testing."""
    entity = Mock()
    entity.entity_id = "k8s://default/pod/test-pod"
    entity.source_name = "kubernetes"
    entity.kind = "Pod"
    entity.name = "test-pod"
    entity.namespace = "default"
    entity.labels = {"app": "test", "version": "1.0"}
    entity.content = "Pod: test-pod\nNamespace: default\nStatus: Running"
    return entity


@pytest.fixture
def mock_github_entity():
    """Create a mock GitHub entity for testing."""
    entity = Mock()
    entity.entity_id = "github/owner/repo/file.py"
    entity.source_name = "github"
    entity.name = "file.py"
    entity.repo_name = "repo"
    entity.repo_owner = "owner"
    entity.path = "src/file.py"
    entity.language = "python"
    entity.content = "def hello_world():\n    print('Hello, World!')"
    return entity


class TestChromaVectorStore:
    """Test cases for ChromaVectorStore."""

    def test_init(self, temp_db_dir):
        """Test vector store initialization."""
        store = ChromaVectorStore(
            persist_directory=temp_db_dir,
            collection_name="test",
            embedding_model="all-MiniLM-L6-v2"
        )
        
        assert store.persist_directory == temp_db_dir
        assert store.collection_name == "test"
        assert store.embedding_model_name == "all-MiniLM-L6-v2"
        assert store.collection is not None

    def test_generate_embedding(self, vector_store):
        """Test embedding generation."""
        text = "This is a test sentence."
        embedding = vector_store._generate_embedding(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    def test_prepare_document_text_k8s(self, vector_store, mock_k8s_entity):
        """Test document text preparation for Kubernetes entity."""
        text = vector_store._prepare_document_text(mock_k8s_entity)
        
        assert "Type: Pod" in text
        assert "Name: test-pod" in text
        assert "Namespace: default" in text
        assert "Labels: app=test, version=1.0" in text
        assert "Content: Pod: test-pod" in text

    def test_prepare_document_text_github(self, vector_store, mock_github_entity):
        """Test document text preparation for GitHub entity."""
        # Fix the mock to not have 'kind' attribute
        delattr(mock_github_entity, 'kind') if hasattr(mock_github_entity, 'kind') else None
        
        text = vector_store._prepare_document_text(mock_github_entity)
        
        assert "Source: github" in text
        assert "Name: file.py" in text
        assert "Repository: repo" in text
        assert "Owner: owner" in text
        assert "Path: src/file.py" in text
        assert "Language: python" in text
        assert "def hello_world()" in text

    def test_extract_metadata_k8s(self, vector_store, mock_k8s_entity):
        """Test metadata extraction for Kubernetes entity."""
        metadata = vector_store._extract_metadata(mock_k8s_entity)
        
        assert metadata["source"] == "kubernetes"
        assert metadata["kind"] == "Pod"
        assert metadata["type"] == "kubernetes"
        assert metadata["namespace"] == "default"
        assert metadata["name"] == "test-pod"
        assert metadata["entity_id"] == "k8s://default/pod/test-pod"

    def test_extract_metadata_github(self, vector_store, mock_github_entity):
        """Test metadata extraction for GitHub entity."""
        # Ensure the mock doesn't have 'kind' attribute to trigger GitHub path
        delattr(mock_github_entity, 'kind') if hasattr(mock_github_entity, 'kind') else None
        
        metadata = vector_store._extract_metadata(mock_github_entity)
        
        assert metadata["source"] == "github"
        assert metadata["type"] == "github"
        assert metadata["repo_name"] == "repo"
        assert metadata["repo_owner"] == "owner"
        assert metadata["language"] == "python"
        assert metadata["name"] == "file.py"

    @pytest.mark.asyncio
    async def test_add_entity(self, vector_store, mock_k8s_entity):
        """Test adding a single entity."""
        doc_id = await vector_store.add_entity(mock_k8s_entity)
        
        assert isinstance(doc_id, str)
        assert "kubernetes" in doc_id
        
        # Verify entity was added
        stats = vector_store.get_collection_stats()
        assert stats["total_documents"] == 1

    @pytest.mark.asyncio
    async def test_add_entities_batch(self, vector_store, mock_k8s_entity, mock_github_entity):
        """Test adding multiple entities in batch."""
        entities = [mock_k8s_entity, mock_github_entity]
        doc_ids = await vector_store.add_entities_batch(entities, batch_size=2)
        
        assert len(doc_ids) == 2
        assert all(isinstance(doc_id, str) for doc_id in doc_ids)
        
        # Verify entities were added
        stats = vector_store.get_collection_stats()
        assert stats["total_documents"] == 2

    @pytest.mark.asyncio
    async def test_search(self, vector_store, mock_k8s_entity):
        """Test basic search functionality."""
        # Add an entity first
        await vector_store.add_entity(mock_k8s_entity)
        
        # Search for it
        results = await vector_store.search("test pod", n_results=5)
        
        assert len(results) > 0
        assert "document" in results[0]
        assert "metadata" in results[0]
        assert "distance" in results[0]
        assert "similarity" in results[0]

    @pytest.mark.asyncio
    async def test_search_by_source(self, vector_store, mock_k8s_entity, mock_github_entity):
        """Test searching by source filter."""
        # Add entities from different sources
        await vector_store.add_entity(mock_k8s_entity)
        await vector_store.add_entity(mock_github_entity)
        
        # Search for Kubernetes entities only
        k8s_results = await vector_store.search_by_source("test", "kubernetes", n_results=5)
        
        assert len(k8s_results) > 0
        assert all(result["metadata"]["source"] == "kubernetes" for result in k8s_results)

    @pytest.mark.asyncio
    async def test_search_kubernetes_by_kind(self, vector_store, mock_k8s_entity):
        """Test searching Kubernetes resources by kind."""
        await vector_store.add_entity(mock_k8s_entity)
        
        results = await vector_store.search_kubernetes_by_kind("test", "Pod", n_results=5)
        
        assert len(results) > 0
        assert all(result["metadata"]["kind"] == "Pod" for result in results)

    @pytest.mark.asyncio
    async def test_search_github_by_repo(self, vector_store, mock_github_entity):
        """Test searching GitHub resources by repository."""
        await vector_store.add_entity(mock_github_entity)
        
        results = await vector_store.search_github_by_repo("python", "repo", n_results=5)
        
        assert len(results) > 0
        assert all(result["metadata"]["repo_name"] == "repo" for result in results)

    def test_get_collection_stats(self, vector_store):
        """Test collection statistics."""
        stats = vector_store.get_collection_stats()
        
        assert "total_documents" in stats
        assert "sources" in stats
        assert "kubernetes_kinds" in stats
        assert "github_repos" in stats
        assert "collection_name" in stats
        assert "embedding_model" in stats
        
        assert stats["collection_name"] == "test_collection"
        assert stats["embedding_model"] == "all-MiniLM-L6-v2"

    def test_reset_collection(self, vector_store, mock_k8s_entity):
        """Test collection reset functionality."""
        # Add an entity
        vector_store.collection.add(
            documents=["test document"],
            metadatas=[{"source": "test"}],
            ids=["test_id"]
        )
        
        # Verify it was added
        assert vector_store.collection.count() == 1
        
        # Reset collection
        vector_store.reset_collection()
        
        # Verify it was reset
        assert vector_store.collection.count() == 0
