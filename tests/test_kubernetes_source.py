"""Tests for the Kubernetes source connector."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.sources.kubernetes import KubernetesSource, KubernetesEntity


@pytest.fixture
def mock_k8s_client():
    """Create mock Kubernetes client."""
    client = Mock()
    client.CoreV1Api.return_value = Mock()
    client.AppsV1Api.return_value = Mock()
    client.NetworkingV1Api.return_value = Mock()
    return client


@pytest.fixture
def k8s_source():
    """Create a KubernetesSource instance."""
    return KubernetesSource()


@pytest.fixture
def mock_pod():
    """Create a mock Kubernetes pod object."""
    pod = Mock()
    pod.metadata = Mock()
    pod.metadata.name = "test-pod"
    pod.metadata.namespace = "default"
    pod.metadata.labels = {"app": "test"}
    pod.metadata.annotations = {"annotation": "value"}
    pod.metadata.creation_timestamp = datetime.now()
    pod.metadata.resource_version = "12345"
    pod.metadata.uid = "test-uid"
    pod.api_version = "v1"
    pod.spec = Mock()
    pod.status = Mock()
    return pod


@pytest.fixture
def mock_service():
    """Create a mock Kubernetes service object."""
    service = Mock()
    service.metadata = Mock()
    service.metadata.name = "test-service"
    service.metadata.namespace = "default"
    service.metadata.labels = {"app": "test"}
    service.metadata.annotations = {}
    service.metadata.creation_timestamp = datetime.now()
    service.metadata.resource_version = "67890"
    service.metadata.uid = "service-uid"
    service.api_version = "v1"
    service.spec = Mock()
    service.status = Mock()
    return service


class TestKubernetesEntity:
    """Test cases for KubernetesEntity."""

    def test_entity_creation(self):
        """Test creating a KubernetesEntity."""
        entity = KubernetesEntity(
            entity_id="test-id",
            name="test-pod",
            namespace="default",
            kind="Pod"
        )
        
        assert entity.entity_id == "test-id"
        assert entity.source_name == "kubernetes"
        assert entity.name == "test-pod"
        assert entity.namespace == "default"
        assert entity.kind == "Pod"
        assert entity.labels == {}
        assert entity.annotations == {}
        assert entity.metadata == {}

    def test_entity_with_labels(self):
        """Test entity creation with labels and annotations."""
        entity = KubernetesEntity(
            entity_id="test-id",
            name="test-pod",
            labels={"app": "test"},
            annotations={"key": "value"}
        )
        
        assert entity.labels == {"app": "test"}
        assert entity.annotations == {"key": "value"}


class TestKubernetesSource:
    """Test cases for KubernetesSource."""

    def test_init(self):
        """Test KubernetesSource initialization."""
        source = KubernetesSource(kubeconfig_path="/test/path", context="test-context")
        
        assert source.kubeconfig_path == "/test/path"
        assert source.context == "test-context"
        assert source.api_client is None
        assert source.v1 is None

    @patch('backend.sources.kubernetes.config')
    @patch('backend.sources.kubernetes.client')
    async def test_initialize_with_kubeconfig(self, mock_client, mock_config, k8s_source):
        """Test initialization with kubeconfig file."""
        k8s_source.kubeconfig_path = "/test/kubeconfig"
        k8s_source.context = "test-context"
        
        await k8s_source.initialize()
        
        mock_config.load_kube_config.assert_called_once_with(
            config_file="/test/kubeconfig", 
            context="test-context"
        )
        assert k8s_source.api_client is not None
        assert k8s_source.v1 is not None

    @patch('backend.sources.kubernetes.config')
    @patch('backend.sources.kubernetes.client')
    async def test_initialize_in_cluster(self, mock_client, mock_config, k8s_source):
        """Test initialization with in-cluster config."""
        mock_config.load_incluster_config.return_value = None
        
        await k8s_source.initialize()
        
        mock_config.load_incluster_config.assert_called_once()
        assert k8s_source.api_client is not None

    @patch('backend.sources.kubernetes.config')
    async def test_initialize_failure(self, mock_config, k8s_source):
        """Test initialization failure."""
        mock_config.load_incluster_config.side_effect = Exception("Config error")
        mock_config.load_kube_config.side_effect = Exception("Config error")
        
        with pytest.raises(ConnectionError, match="Failed to initialize Kubernetes client"):
            await k8s_source.initialize()

    def test_create_entity_from_k8s_object(self, k8s_source, mock_pod):
        """Test creating entity from Kubernetes object."""
        with patch.object(k8s_source, 'api_client') as mock_api_client:
            mock_api_client.sanitize_for_serialization.return_value = {"test": "data"}
            
            with patch.object(k8s_source, '_get_cluster_name', return_value="test-cluster"):
                entity = k8s_source._create_entity_from_k8s_object(mock_pod, "Pod")
        
        assert entity.entity_id == "k8s://default/pod/test-pod"
        assert entity.name == "test-pod"
        assert entity.namespace == "default"
        assert entity.kind == "Pod"
        assert entity.api_version == "v1"
        assert entity.labels == {"app": "test"}
        assert entity.annotations == {"annotation": "value"}
        assert entity.uid == "test-uid"
        assert "test-cluster" in entity.metadata["cluster_name"]

    def test_create_entity_cluster_wide(self, k8s_source):
        """Test creating entity for cluster-wide resource."""
        namespace_obj = Mock()
        namespace_obj.metadata = Mock()
        namespace_obj.metadata.name = "test-namespace"
        namespace_obj.metadata.namespace = None
        namespace_obj.metadata.labels = {}
        namespace_obj.metadata.annotations = {}
        namespace_obj.metadata.creation_timestamp = datetime.now()
        namespace_obj.metadata.resource_version = "123"
        namespace_obj.metadata.uid = "ns-uid"
        namespace_obj.api_version = "v1"
        
        with patch.object(k8s_source, 'api_client') as mock_api_client:
            mock_api_client.sanitize_for_serialization.return_value = {"test": "data"}
            
            with patch.object(k8s_source, '_get_cluster_name', return_value="test-cluster"):
                entity = k8s_source._create_entity_from_k8s_object(namespace_obj, "Namespace")
        
        assert entity.entity_id == "k8s://cluster-wide/namespace/test-namespace"
        assert entity.namespace == "cluster-wide"

    @patch('backend.sources.kubernetes.config')
    def test_get_cluster_name(self, mock_config, k8s_source):
        """Test getting cluster name."""
        mock_contexts = [{"context": {"cluster": "test-cluster"}}]
        mock_active = {"context": {"cluster": "test-cluster"}}
        mock_config.list_kube_config_contexts.return_value = (mock_contexts, mock_active)
        
        cluster_name = k8s_source._get_cluster_name()
        
        assert cluster_name == "test-cluster"

    @patch('backend.sources.kubernetes.config')
    def test_get_cluster_name_failure(self, mock_config, k8s_source):
        """Test getting cluster name when config fails."""
        mock_config.list_kube_config_contexts.side_effect = Exception("Config error")
        
        cluster_name = k8s_source._get_cluster_name()
        
        assert cluster_name == "unknown-cluster"

    @pytest.mark.asyncio
    async def test_get_pods(self, k8s_source, mock_pod):
        """Test getting pods from cluster."""
        mock_v1 = Mock()
        mock_pods_list = Mock()
        mock_pods_list.items = [mock_pod]
        mock_v1.list_pod_for_all_namespaces.return_value = mock_pods_list
        k8s_source.v1 = mock_v1
        
        with patch.object(k8s_source, 'api_client') as mock_api_client:
            mock_api_client.sanitize_for_serialization.return_value = {"test": "data"}
            
            with patch.object(k8s_source, '_get_cluster_name', return_value="test-cluster"):
                entities = []
                async for entity in k8s_source.get_pods():
                    entities.append(entity)
        
        assert len(entities) == 1
        assert entities[0].kind == "Pod"
        assert entities[0].name == "test-pod"

    @pytest.mark.asyncio
    async def test_get_pods_namespaced(self, k8s_source, mock_pod):
        """Test getting pods from specific namespace."""
        mock_v1 = Mock()
        mock_pods_list = Mock()
        mock_pods_list.items = [mock_pod]
        mock_v1.list_namespaced_pod.return_value = mock_pods_list
        k8s_source.v1 = mock_v1
        
        with patch.object(k8s_source, 'api_client') as mock_api_client:
            mock_api_client.sanitize_for_serialization.return_value = {"test": "data"}
            
            with patch.object(k8s_source, '_get_cluster_name', return_value="test-cluster"):
                entities = []
                async for entity in k8s_source.get_pods(namespace="default"):
                    entities.append(entity)
        
        assert len(entities) == 1
        mock_v1.list_namespaced_pod.assert_called_once_with(namespace="default")

    @pytest.mark.asyncio
    async def test_get_services(self, k8s_source, mock_service):
        """Test getting services from cluster."""
        mock_v1 = Mock()
        mock_services_list = Mock()
        mock_services_list.items = [mock_service]
        mock_v1.list_service_for_all_namespaces.return_value = mock_services_list
        k8s_source.v1 = mock_v1
        
        with patch.object(k8s_source, 'api_client') as mock_api_client:
            mock_api_client.sanitize_for_serialization.return_value = {"test": "data"}
            
            with patch.object(k8s_source, '_get_cluster_name', return_value="test-cluster"):
                entities = []
                async for entity in k8s_source.get_services():
                    entities.append(entity)
        
        assert len(entities) == 1
        assert entities[0].kind == "Service"
        assert entities[0].name == "test-service"

    @pytest.mark.asyncio
    async def test_get_cluster_summary(self, k8s_source):
        """Test getting cluster summary."""
        # Mock the v1 API client
        mock_v1 = Mock()
        
        # Mock different resource lists
        mock_pods = Mock()
        mock_pods.items = [Mock(), Mock()]  # 2 pods
        mock_v1.list_pod_for_all_namespaces.return_value = mock_pods
        
        mock_services = Mock()
        mock_services.items = [Mock()]  # 1 service
        mock_v1.list_service_for_all_namespaces.return_value = mock_services
        
        mock_namespaces = Mock()
        mock_namespaces.items = [Mock(), Mock(), Mock()]  # 3 namespaces
        mock_v1.list_namespace.return_value = mock_namespaces
        
        mock_configmaps = Mock()
        mock_configmaps.items = [Mock()]  # 1 configmap
        mock_v1.list_config_map_for_all_namespaces.return_value = mock_configmaps
        
        mock_secrets = Mock()
        mock_secrets.items = [Mock(), Mock(), Mock(), Mock()]  # 4 secrets
        mock_v1.list_secret_for_all_namespaces.return_value = mock_secrets
        
        # Mock the apps_v1 API client
        mock_apps_v1 = Mock()
        mock_deployments = Mock()
        mock_deployments.items = [Mock()]  # 1 deployment
        mock_apps_v1.list_deployment_for_all_namespaces.return_value = mock_deployments
        
        k8s_source.v1 = mock_v1
        k8s_source.apps_v1 = mock_apps_v1
        
        with patch.object(k8s_source, '_get_cluster_name', return_value="test-cluster"):
            with patch.object(k8s_source, 'initialize'):
                summary = await k8s_source.get_cluster_summary()
        
        assert summary["cluster_name"] == "test-cluster"
        assert summary["resources"]["pods"] == 2
        assert summary["resources"]["services"] == 1
        assert summary["resources"]["namespaces"] == 3
        assert summary["resources"]["deployments"] == 1
        assert summary["resources"]["configmaps"] == 1
        assert summary["resources"]["secrets"] == 4
        assert "timestamp" in summary

    @pytest.mark.asyncio
    async def test_generate_entities(self, k8s_source, mock_pod, mock_service):
        """Test generating all entities from cluster."""
        # Setup mocks
        k8s_source.v1 = Mock()
        k8s_source.apps_v1 = Mock()
        k8s_source.networking_v1 = Mock()
        
        # Mock namespace list
        mock_namespaces = Mock()
        mock_namespaces.items = []
        k8s_source.v1.list_namespace.return_value = mock_namespaces
        
        # Mock pod list
        mock_pods = Mock()
        mock_pods.items = [mock_pod]
        k8s_source.v1.list_pod_for_all_namespaces.return_value = mock_pods
        
        # Mock service list
        mock_services = Mock()
        mock_services.items = [mock_service]
        k8s_source.v1.list_service_for_all_namespaces.return_value = mock_services
        
        # Mock other resources as empty
        empty_list = Mock()
        empty_list.items = []
        k8s_source.apps_v1.list_deployment_for_all_namespaces.return_value = empty_list
        k8s_source.v1.list_config_map_for_all_namespaces.return_value = empty_list
        k8s_source.v1.list_secret_for_all_namespaces.return_value = empty_list
        k8s_source.networking_v1.list_ingress_for_all_namespaces.return_value = empty_list
        
        with patch.object(k8s_source, 'initialize'):
            with patch.object(k8s_source, 'api_client') as mock_api_client:
                mock_api_client.sanitize_for_serialization.return_value = {"test": "data"}
                
                with patch.object(k8s_source, '_get_cluster_name', return_value="test-cluster"):
                    entities = []
                    async for entity in k8s_source.generate_entities():
                        entities.append(entity)
        
        # Should have 2 entities: 1 pod + 1 service
        assert len(entities) == 2
        entity_kinds = [e.kind for e in entities]
        assert "Pod" in entity_kinds
        assert "Service" in entity_kinds
