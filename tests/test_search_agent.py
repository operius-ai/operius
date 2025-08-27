"""Tests for the search agent functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.search_agent import SearchAgent


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = Mock()
    store.search = AsyncMock()
    store.search_by_source = AsyncMock()
    store.search_kubernetes_by_kind = AsyncMock()
    store.search_github_by_repo = AsyncMock()
    store.get_collection_stats = Mock()
    return store


@pytest.fixture
def search_agent(mock_vector_store):
    """Create a SearchAgent instance with mock vector store."""
    return SearchAgent(mock_vector_store)


@pytest.fixture
def mock_search_results():
    """Create mock search results."""
    return [
        {
            "document": "Pod: test-pod\nNamespace: default\nStatus: Running",
            "metadata": {
                "source": "kubernetes",
                "kind": "Pod",
                "name": "test-pod",
                "namespace": "default"
            },
            "distance": 0.2,
            "similarity": 0.8
        },
        {
            "document": "Service: test-service\nNamespace: default\nType: ClusterIP",
            "metadata": {
                "source": "kubernetes",
                "kind": "Service",
                "name": "test-service",
                "namespace": "default"
            },
            "distance": 0.3,
            "similarity": 0.7
        }
    ]


class TestSearchAgent:
    """Test cases for SearchAgent."""

    def test_init(self, mock_vector_store):
        """Test SearchAgent initialization."""
        agent = SearchAgent(mock_vector_store)
        assert agent.vector_store == mock_vector_store

    @pytest.mark.asyncio
    async def test_search_basic(self, search_agent, mock_vector_store, mock_search_results):
        """Test basic search functionality."""
        mock_vector_store.search.return_value = mock_search_results
        
        result = await search_agent.search("test query", max_results=5)
        
        assert result["query"] == "test query"
        assert result["total_results"] == 2
        assert result["filters_applied"] == {}
        assert len(result["results"]) == 2
        assert "timestamp" in result
        
        mock_vector_store.search.assert_called_once_with(
            query="test query",
            n_results=5,
            filters=None
        )

    @pytest.mark.asyncio
    async def test_search_with_filters(self, search_agent, mock_vector_store, mock_search_results):
        """Test search with filters."""
        mock_vector_store.search.return_value = mock_search_results
        
        result = await search_agent.search(
            "test query",
            source_filter="kubernetes",
            additional_filters={"namespace": "default"}
        )
        
        expected_filters = {"source": "kubernetes", "namespace": "default"}
        assert result["filters_applied"] == expected_filters
        
        mock_vector_store.search.assert_called_once_with(
            query="test query",
            n_results=10,
            filters=expected_filters
        )

    @pytest.mark.asyncio
    async def test_search_kubernetes(self, search_agent, mock_vector_store, mock_search_results):
        """Test Kubernetes-specific search."""
        mock_vector_store.search.return_value = mock_search_results
        
        result = await search_agent.search_kubernetes(
            "test pods",
            resource_kind="Pod",
            namespace="default",
            max_results=5
        )
        
        assert result["query"] == "test pods"
        assert result["search_type"] == "kubernetes"
        assert result["resource_kind"] == "Pod"
        assert result["namespace"] == "default"
        assert result["total_results"] == 2
        
        expected_filters = {"source": "kubernetes", "kind": "Pod", "namespace": "default"}
        mock_vector_store.search.assert_called_once_with(
            query="test pods",
            n_results=5,
            filters=expected_filters
        )

    @pytest.mark.asyncio
    async def test_search_github(self, search_agent, mock_vector_store):
        """Test GitHub-specific search."""
        github_results = [
            {
                "document": "def hello_world():\n    print('Hello, World!')",
                "metadata": {
                    "source": "github",
                    "repo_name": "test-repo",
                    "language": "python",
                    "name": "hello.py"
                },
                "distance": 0.1,
                "similarity": 0.9
            }
        ]
        mock_vector_store.search.return_value = github_results
        
        result = await search_agent.search_github(
            "python function",
            repo_name="test-repo",
            language="python"
        )
        
        assert result["query"] == "python function"
        assert result["search_type"] == "github"
        assert result["repo_name"] == "test-repo"
        assert result["language"] == "python"
        assert result["total_results"] == 1
        
        expected_filters = {"source": "github", "repo_name": "test-repo", "language": "python"}
        mock_vector_store.search.assert_called_once_with(
            query="python function",
            n_results=10,
            filters=expected_filters
        )

    @pytest.mark.asyncio
    async def test_find_related_resources(self, search_agent, mock_vector_store, mock_search_results):
        """Test finding related resources."""
        mock_vector_store.search.return_value = mock_search_results
        
        result = await search_agent.find_related_resources("test-entity-id", max_results=3)
        
        assert result["entity_id"] == "test-entity-id"
        assert result["total_found"] == 2
        assert len(result["related_resources"]) == 2
        
        mock_vector_store.search.assert_called_once_with(
            query="test-entity-id",
            n_results=3
        )

    @pytest.mark.asyncio
    async def test_get_cluster_overview(self, search_agent, mock_vector_store):
        """Test getting cluster overview."""
        mock_stats = {
            "total_documents": 100,
            "sources": {"kubernetes": 60, "github": 40},
            "kubernetes_kinds": {"Pod": 20, "Service": 15},
            "github_repos": {"repo1": 25, "repo2": 15}
        }
        mock_vector_store.get_collection_stats.return_value = mock_stats
        
        k8s_samples = [mock_search_results[0]]
        github_samples = [
            {
                "document": "def test():\n    pass",
                "metadata": {"source": "github", "name": "test.py"},
                "distance": 0.1,
                "similarity": 0.9
            }
        ]
        
        mock_vector_store.search_by_source.side_effect = [k8s_samples, github_samples]
        
        result = await search_agent.get_cluster_overview()
        
        assert result["statistics"] == mock_stats
        assert "kubernetes" in result["sample_data"]
        assert "github" in result["sample_data"]
        assert "overview_timestamp" in result
        
        # Verify search_by_source was called for both sources
        assert mock_vector_store.search_by_source.call_count == 2

    @pytest.mark.asyncio
    async def test_analyze_query_intent_kubernetes(self, search_agent):
        """Test query intent analysis for Kubernetes queries."""
        result = await search_agent.analyze_query_intent("show me running pods")
        
        assert "kubernetes" in result["detected_intents"]
        assert result["suggested_filters"]["source"] == "kubernetes"
        assert result["suggested_filters"]["kind"] == "Pod"
        assert any("search_kubernetes()" in suggestion for suggestion in result["search_suggestions"])

    @pytest.mark.asyncio
    async def test_analyze_query_intent_github(self, search_agent):
        """Test query intent analysis for GitHub queries."""
        result = await search_agent.analyze_query_intent("find python code files")
        
        assert "github" in result["detected_intents"]
        assert result["suggested_filters"]["source"] == "github"
        assert result["suggested_filters"]["language"] == "python"
        assert any("search_github()" in suggestion for suggestion in result["search_suggestions"])

    @pytest.mark.asyncio
    async def test_analyze_query_intent_mixed(self, search_agent):
        """Test query intent analysis for mixed queries."""
        result = await search_agent.analyze_query_intent("kubernetes deployment with python code")
        
        assert "kubernetes" in result["detected_intents"]
        assert "github" in result["detected_intents"]
        assert result["suggested_filters"]["language"] == "python"

    @pytest.mark.asyncio
    async def test_analyze_query_intent_no_keywords(self, search_agent):
        """Test query intent analysis with no specific keywords."""
        result = await search_agent.analyze_query_intent("general search query")
        
        assert result["detected_intents"] == []
        assert any("Try adding keywords" in suggestion for suggestion in result["search_suggestions"])

    def test_format_search_results_empty(self, search_agent):
        """Test formatting empty search results."""
        result = search_agent.format_search_results([])
        assert result == "No results found."

    def test_format_search_results_kubernetes(self, search_agent, mock_search_results):
        """Test formatting Kubernetes search results."""
        result = search_agent.format_search_results(mock_search_results[:1])
        
        assert "1. [KUBERNETES] test-pod (similarity: 0.800)" in result
        assert "Kind: Pod" in result
        assert "Namespace: default" in result

    def test_format_search_results_github(self, search_agent):
        """Test formatting GitHub search results."""
        github_results = [
            {
                "document": "def hello():\n    pass",
                "metadata": {
                    "source": "github",
                    "name": "hello.py",
                    "repo_name": "test-repo",
                    "language": "python"
                },
                "similarity": 0.95
            }
        ]
        
        result = search_agent.format_search_results(github_results)
        
        assert "[GITHUB] hello.py (similarity: 0.950)" in result
        assert "Repository: test-repo" in result
        assert "Language: python" in result

    def test_format_search_results_with_content(self, search_agent, mock_search_results):
        """Test formatting search results with content preview."""
        result = search_agent.format_search_results(mock_search_results[:1], show_content=True)
        
        assert "Content: Pod: test-pod" in result
        assert "Namespace: default" in result

    def test_format_search_results_long_content(self, search_agent):
        """Test formatting search results with long content."""
        long_content = "A" * 300  # Content longer than 200 chars
        results = [
            {
                "document": long_content,
                "metadata": {"source": "test", "name": "test"},
                "similarity": 0.8
            }
        ]
        
        result = search_agent.format_search_results(results, show_content=True)
        
        # Should truncate content and add "..."
        assert "A" * 200 + "..." in result
