"""Tests for the data ingestion pipeline."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.ingestion_pipeline import DataIngestionPipeline


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = Mock()
    store.add_entities_batch = AsyncMock()
    store.get_collection_stats = Mock()
    return store


@pytest.fixture
def mock_k8s_source():
    """Create a mock Kubernetes source."""
    source = Mock()
    source.generate_entities = AsyncMock()
    source.get_cluster_summary = AsyncMock()
    return source


@pytest.fixture
def mock_k8s_entities():
    """Create mock Kubernetes entities."""
    entities = []
    for i in range(3):
        entity = Mock()
        entity.entity_id = f"k8s://default/pod/test-pod-{i}"
        entity.source_name = "kubernetes"
        entity.kind = "Pod"
        entity.name = f"test-pod-{i}"
        entity.namespace = "default"
        entities.append(entity)
    return entities


@pytest.fixture
def pipeline(mock_vector_store):
    """Create a DataIngestionPipeline instance."""
    return DataIngestionPipeline(
        vector_store=mock_vector_store,
        github_token="test-token",
        kubeconfig_path="/test/kubeconfig",
        k8s_context="test-context"
    )


class TestDataIngestionPipeline:
    """Test cases for DataIngestionPipeline."""

    def test_init(self, mock_vector_store):
        """Test pipeline initialization."""
        pipeline = DataIngestionPipeline(
            vector_store=mock_vector_store,
            github_token="test-token",
            kubeconfig_path="/test/kubeconfig",
            k8s_context="test-context"
        )
        
        assert pipeline.vector_store == mock_vector_store
        assert pipeline.github_token == "test-token"
        assert pipeline.kubeconfig_path == "/test/kubeconfig"
        assert pipeline.k8s_context == "test-context"
        assert pipeline.k8s_source is not None

    @pytest.mark.asyncio
    async def test_ingest_kubernetes_data_success(self, pipeline, mock_k8s_entities):
        """Test successful Kubernetes data ingestion."""
        # Mock the k8s source to return entities
        async def mock_generate():
            for entity in mock_k8s_entities:
                yield entity
        
        pipeline.k8s_source.generate_entities = mock_generate
        pipeline.vector_store.add_entities_batch.return_value = ["doc1", "doc2", "doc3"]
        
        result = await pipeline.ingest_kubernetes_data()
        
        assert result["source"] == "kubernetes"
        assert result["success"] is True
        assert result["entities_processed"] == 3
        assert result["documents_added"] == 3
        assert "duration_seconds" in result
        assert "start_time" in result
        assert "end_time" in result
        
        # Verify vector store was called
        pipeline.vector_store.add_entities_batch.assert_called_once()
        call_args = pipeline.vector_store.add_entities_batch.call_args[0]
        assert len(call_args[0]) == 3  # 3 entities

    @pytest.mark.asyncio
    async def test_ingest_kubernetes_data_with_namespace_filter(self, pipeline, mock_k8s_entities):
        """Test Kubernetes ingestion with namespace filter."""
        # Add entities from different namespaces
        mock_k8s_entities[0].namespace = "default"
        mock_k8s_entities[1].namespace = "kube-system"
        mock_k8s_entities[2].namespace = "default"
        
        async def mock_generate():
            for entity in mock_k8s_entities:
                yield entity
        
        pipeline.k8s_source.generate_entities = mock_generate
        pipeline.vector_store.add_entities_batch.return_value = ["doc1", "doc2"]
        
        result = await pipeline.ingest_kubernetes_data(namespaces=["default"])
        
        assert result["success"] is True
        assert result["entities_processed"] == 2  # Only default namespace entities
        
        # Check that only default namespace entities were passed to vector store
        call_args = pipeline.vector_store.add_entities_batch.call_args[0]
        entities = call_args[0]
        assert len(entities) == 2
        assert all(e.namespace == "default" for e in entities)

    @pytest.mark.asyncio
    async def test_ingest_kubernetes_data_with_resource_filter(self, pipeline, mock_k8s_entities):
        """Test Kubernetes ingestion with resource type filter."""
        # Set different resource types
        mock_k8s_entities[0].kind = "Pod"
        mock_k8s_entities[1].kind = "Service"
        mock_k8s_entities[2].kind = "Pod"
        
        async def mock_generate():
            for entity in mock_k8s_entities:
                yield entity
        
        pipeline.k8s_source.generate_entities = mock_generate
        pipeline.vector_store.add_entities_batch.return_value = ["doc1", "doc2"]
        
        result = await pipeline.ingest_kubernetes_data(resource_types=["Pod"])
        
        assert result["success"] is True
        assert result["entities_processed"] == 2  # Only Pod entities
        
        # Check that only Pod entities were passed to vector store
        call_args = pipeline.vector_store.add_entities_batch.call_args[0]
        entities = call_args[0]
        assert len(entities) == 2
        assert all(e.kind == "Pod" for e in entities)

    @pytest.mark.asyncio
    async def test_ingest_kubernetes_data_no_entities(self, pipeline):
        """Test Kubernetes ingestion when no entities are found."""
        async def mock_generate():
            return
            yield  # This will never execute
        
        pipeline.k8s_source.generate_entities = mock_generate
        
        result = await pipeline.ingest_kubernetes_data()
        
        assert result["success"] is True
        assert result["entities_processed"] == 0
        assert result["documents_added"] == 0
        
        # Vector store should not be called
        pipeline.vector_store.add_entities_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_ingest_kubernetes_data_failure(self, pipeline):
        """Test Kubernetes ingestion failure."""
        pipeline.k8s_source.generate_entities.side_effect = Exception("K8s connection failed")
        
        result = await pipeline.ingest_kubernetes_data()
        
        assert result["success"] is False
        assert result["source"] == "kubernetes"
        assert "K8s connection failed" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_ingest_github_repo_not_implemented(self, pipeline):
        """Test GitHub repository ingestion (not yet implemented)."""
        result = await pipeline.ingest_github_repo("owner/repo", branch="main")
        
        assert result["success"] is False
        assert result["source"] == "github"
        assert result["repo_name"] == "owner/repo"
        assert "not yet implemented" in result["message"]

    @pytest.mark.asyncio
    async def test_run_full_ingestion_k8s_only(self, pipeline, mock_k8s_entities):
        """Test full ingestion pipeline with only Kubernetes data."""
        # Mock successful K8s ingestion
        async def mock_generate():
            for entity in mock_k8s_entities:
                yield entity
        
        pipeline.k8s_source.generate_entities = mock_generate
        pipeline.vector_store.add_entities_batch.return_value = ["doc1", "doc2", "doc3"]
        pipeline.vector_store.get_collection_stats.return_value = {
            "total_documents": 3,
            "sources": {"kubernetes": 3}
        }
        
        result = await pipeline.run_full_ingestion()
        
        assert "pipeline_start" in result
        assert "pipeline_end" in result
        assert "total_duration" in result
        assert "sources" in result
        assert "summary" in result
        
        # Check Kubernetes results
        k8s_result = result["sources"]["kubernetes"]
        assert k8s_result["success"] is True
        assert k8s_result["entities_processed"] == 3
        
        # Check summary
        summary = result["summary"]
        assert summary["total_entities_processed"] == 3
        assert summary["total_documents_added"] == 3
        assert summary["successful_sources"] == 1

    @pytest.mark.asyncio
    async def test_run_full_ingestion_with_github_repos(self, pipeline, mock_k8s_entities):
        """Test full ingestion pipeline with GitHub repositories."""
        # Mock K8s ingestion
        async def mock_generate():
            for entity in mock_k8s_entities:
                yield entity
        
        pipeline.k8s_source.generate_entities = mock_generate
        pipeline.vector_store.add_entities_batch.return_value = ["doc1", "doc2", "doc3"]
        pipeline.vector_store.get_collection_stats.return_value = {
            "total_documents": 3,
            "sources": {"kubernetes": 3}
        }
        
        github_repos = ["owner1/repo1", "owner2/repo2"]
        result = await pipeline.run_full_ingestion(github_repos=github_repos)
        
        # Check that GitHub ingestion was attempted
        assert "github" in result["sources"]
        github_results = result["sources"]["github"]
        assert len(github_results) == 2
        
        # All GitHub results should fail (not implemented)
        assert all(not repo_result["success"] for repo_result in github_results)

    @pytest.mark.asyncio
    async def test_run_full_ingestion_with_namespace_filter(self, pipeline, mock_k8s_entities):
        """Test full ingestion with namespace filtering."""
        # Set up entities in different namespaces
        mock_k8s_entities[0].namespace = "default"
        mock_k8s_entities[1].namespace = "kube-system"
        mock_k8s_entities[2].namespace = "default"
        
        async def mock_generate():
            for entity in mock_k8s_entities:
                yield entity
        
        pipeline.k8s_source.generate_entities = mock_generate
        pipeline.vector_store.add_entities_batch.return_value = ["doc1", "doc2"]
        pipeline.vector_store.get_collection_stats.return_value = {
            "total_documents": 2,
            "sources": {"kubernetes": 2}
        }
        
        result = await pipeline.run_full_ingestion(k8s_namespaces=["default"])
        
        # Should only process entities from default namespace
        k8s_result = result["sources"]["kubernetes"]
        assert k8s_result["entities_processed"] == 2
        assert result["summary"]["total_entities_processed"] == 2

    @pytest.mark.asyncio
    async def test_get_cluster_summary_success(self, pipeline):
        """Test getting cluster summary successfully."""
        expected_summary = {
            "cluster_name": "test-cluster",
            "timestamp": datetime.now().isoformat(),
            "resources": {
                "pods": 5,
                "services": 3,
                "deployments": 2
            }
        }
        
        pipeline.k8s_source.get_cluster_summary.return_value = expected_summary
        
        result = await pipeline.get_cluster_summary()
        
        assert result == expected_summary
        pipeline.k8s_source.get_cluster_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cluster_summary_failure(self, pipeline):
        """Test getting cluster summary with failure."""
        pipeline.k8s_source.get_cluster_summary.side_effect = Exception("Connection failed")
        
        result = await pipeline.get_cluster_summary()
        
        assert result["success"] is False
        assert "Connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_cluster_wide_namespace_handling(self, pipeline):
        """Test handling of cluster-wide resources."""
        # Create entities with cluster-wide namespace
        cluster_entity = Mock()
        cluster_entity.entity_id = "k8s://cluster-wide/namespace/test-ns"
        cluster_entity.source_name = "kubernetes"
        cluster_entity.kind = "Namespace"
        cluster_entity.name = "test-ns"
        cluster_entity.namespace = "cluster-wide"
        
        async def mock_generate():
            yield cluster_entity
        
        pipeline.k8s_source.generate_entities = mock_generate
        pipeline.vector_store.add_entities_batch.return_value = ["doc1"]
        
        # Test with namespace filter - cluster-wide should be included
        result = await pipeline.ingest_kubernetes_data(namespaces=["default"])
        
        assert result["success"] is True
        assert result["entities_processed"] == 1  # cluster-wide entity included
        
        call_args = pipeline.vector_store.add_entities_batch.call_args[0]
        entities = call_args[0]
        assert len(entities) == 1
        assert entities[0].namespace == "cluster-wide"
