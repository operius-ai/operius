"""Kubernetes source implementation for syncing cluster metadata and resources."""

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional
from dataclasses import dataclass

from kubernetes import client, config
from kubernetes.client.rest import ApiException


@dataclass
class KubernetesEntity:
    """Base entity for Kubernetes resources."""
    entity_id: str
    source_name: str = "kubernetes"
    name: str = ""
    namespace: str = ""
    kind: str = ""
    api_version: str = ""
    labels: Dict[str, str] = None
    annotations: Dict[str, str] = None
    creation_timestamp: datetime = None
    resource_version: str = ""
    uid: str = ""
    content: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.annotations is None:
            self.annotations = {}
        if self.metadata is None:
            self.metadata = {}


class KubernetesSource:
    """Kubernetes source connector integrates with the Kubernetes API to extract cluster metadata.
    
    Connects to your Kubernetes cluster and extracts:
    - Pods, Services, Deployments, ConfigMaps, Secrets
    - Namespaces and cluster-wide resources
    - Resource relationships and dependencies
    """

    def __init__(self, kubeconfig_path: Optional[str] = None, context: Optional[str] = None):
        """Initialize Kubernetes source.
        
        Args:
            kubeconfig_path: Path to kubeconfig file (None for in-cluster config)
            context: Kubernetes context to use (None for current context)
        """
        self.kubeconfig_path = kubeconfig_path
        self.context = context
        self.api_client = None
        self.v1 = None
        self.apps_v1 = None
        self.networking_v1 = None
        
    async def initialize(self):
        """Initialize Kubernetes client."""
        try:
            if self.kubeconfig_path:
                config.load_kube_config(config_file=self.kubeconfig_path, context=self.context)
            else:
                # Try in-cluster config first, fallback to default kubeconfig
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    config.load_kube_config(context=self.context)
            
            self.api_client = client.ApiClient()
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.networking_v1 = client.NetworkingV1Api()
            
        except Exception as e:
            raise ConnectionError(f"Failed to initialize Kubernetes client: {e}")

    def _create_entity_from_k8s_object(self, obj: Any, kind: str) -> KubernetesEntity:
        """Create a KubernetesEntity from a Kubernetes API object.
        
        Args:
            obj: Kubernetes API object
            kind: Resource kind (Pod, Service, etc.)
            
        Returns:
            KubernetesEntity instance
        """
        metadata = obj.metadata
        
        # Create entity ID
        namespace = getattr(metadata, 'namespace', '') or 'cluster-wide'
        entity_id = f"k8s://{namespace}/{kind.lower()}/{metadata.name}"
        
        # Parse creation timestamp
        creation_timestamp = None
        if metadata.creation_timestamp:
            creation_timestamp = metadata.creation_timestamp
        
        # Convert object to dict for content
        obj_dict = self.api_client.sanitize_for_serialization(obj)
        content = json.dumps(obj_dict, indent=2, default=str)
        
        # Extract key metadata
        resource_metadata = {
            "cluster_name": self._get_cluster_name(),
            "resource_type": kind,
            "api_version": obj.api_version,
            "spec": getattr(obj, 'spec', None),
            "status": getattr(obj, 'status', None),
        }
        
        return KubernetesEntity(
            entity_id=entity_id,
            name=metadata.name,
            namespace=namespace,
            kind=kind,
            api_version=obj.api_version,
            labels=metadata.labels or {},
            annotations=metadata.annotations or {},
            creation_timestamp=creation_timestamp,
            resource_version=metadata.resource_version,
            uid=metadata.uid,
            content=content,
            metadata=resource_metadata
        )

    def _get_cluster_name(self) -> str:
        """Get cluster name from current context."""
        try:
            contexts, active_context = config.list_kube_config_contexts()
            if active_context:
                return active_context.get('context', {}).get('cluster', 'unknown-cluster')
        except Exception:
            pass
        return 'unknown-cluster'

    async def get_pods(self, namespace: Optional[str] = None) -> AsyncGenerator[KubernetesEntity, None]:
        """Get all pods from the cluster.
        
        Args:
            namespace: Specific namespace to query (None for all namespaces)
            
        Yields:
            KubernetesEntity for each pod
        """
        try:
            if namespace:
                pods = self.v1.list_namespaced_pod(namespace=namespace)
            else:
                pods = self.v1.list_pod_for_all_namespaces()
                
            for pod in pods.items:
                yield self._create_entity_from_k8s_object(pod, "Pod")
                
        except ApiException as e:
            print(f"Error fetching pods: {e}")

    async def get_services(self, namespace: Optional[str] = None) -> AsyncGenerator[KubernetesEntity, None]:
        """Get all services from the cluster."""
        try:
            if namespace:
                services = self.v1.list_namespaced_service(namespace=namespace)
            else:
                services = self.v1.list_service_for_all_namespaces()
                
            for service in services.items:
                yield self._create_entity_from_k8s_object(service, "Service")
                
        except ApiException as e:
            print(f"Error fetching services: {e}")

    async def get_deployments(self, namespace: Optional[str] = None) -> AsyncGenerator[KubernetesEntity, None]:
        """Get all deployments from the cluster."""
        try:
            if namespace:
                deployments = self.apps_v1.list_namespaced_deployment(namespace=namespace)
            else:
                deployments = self.apps_v1.list_deployment_for_all_namespaces()
                
            for deployment in deployments.items:
                yield self._create_entity_from_k8s_object(deployment, "Deployment")
                
        except ApiException as e:
            print(f"Error fetching deployments: {e}")

    async def get_configmaps(self, namespace: Optional[str] = None) -> AsyncGenerator[KubernetesEntity, None]:
        """Get all configmaps from the cluster."""
        try:
            if namespace:
                configmaps = self.v1.list_namespaced_config_map(namespace=namespace)
            else:
                configmaps = self.v1.list_config_map_for_all_namespaces()
                
            for configmap in configmaps.items:
                yield self._create_entity_from_k8s_object(configmap, "ConfigMap")
                
        except ApiException as e:
            print(f"Error fetching configmaps: {e}")

    async def get_secrets(self, namespace: Optional[str] = None) -> AsyncGenerator[KubernetesEntity, None]:
        """Get all secrets from the cluster."""
        try:
            if namespace:
                secrets = self.v1.list_namespaced_secret(namespace=namespace)
            else:
                secrets = self.v1.list_secret_for_all_namespaces()
                
            for secret in secrets.items:
                # Don't include actual secret data in content for security
                secret_copy = self.api_client.sanitize_for_serialization(secret)
                if 'data' in secret_copy:
                    secret_copy['data'] = {k: '[REDACTED]' for k in secret_copy['data'].keys()}
                
                entity = self._create_entity_from_k8s_object(secret, "Secret")
                entity.content = json.dumps(secret_copy, indent=2, default=str)
                yield entity
                
        except ApiException as e:
            print(f"Error fetching secrets: {e}")

    async def get_namespaces(self) -> AsyncGenerator[KubernetesEntity, None]:
        """Get all namespaces from the cluster."""
        try:
            namespaces = self.v1.list_namespace()
            for namespace in namespaces.items:
                yield self._create_entity_from_k8s_object(namespace, "Namespace")
                
        except ApiException as e:
            print(f"Error fetching namespaces: {e}")

    async def get_ingresses(self, namespace: Optional[str] = None) -> AsyncGenerator[KubernetesEntity, None]:
        """Get all ingresses from the cluster."""
        try:
            if namespace:
                ingresses = self.networking_v1.list_namespaced_ingress(namespace=namespace)
            else:
                ingresses = self.networking_v1.list_ingress_for_all_namespaces()
                
            for ingress in ingresses.items:
                yield self._create_entity_from_k8s_object(ingress, "Ingress")
                
        except ApiException as e:
            print(f"Error fetching ingresses: {e}")

    async def generate_entities(self) -> AsyncGenerator[KubernetesEntity, None]:
        """Generate all entities from the Kubernetes cluster.
        
        Yields:
            KubernetesEntity for each resource in the cluster
        """
        await self.initialize()
        
        # Get all resource types
        resource_generators = [
            self.get_namespaces(),
            self.get_pods(),
            self.get_services(),
            self.get_deployments(),
            self.get_configmaps(),
            self.get_secrets(),
            self.get_ingresses(),
        ]
        
        for generator in resource_generators:
            async for entity in generator:
                yield entity

    async def get_cluster_summary(self) -> Dict[str, Any]:
        """Get a summary of cluster resources.
        
        Returns:
            Dictionary with resource counts and cluster info
        """
        await self.initialize()
        
        summary = {
            "cluster_name": self._get_cluster_name(),
            "timestamp": datetime.now().isoformat(),
            "resources": {}
        }
        
        try:
            # Count resources
            pods = self.v1.list_pod_for_all_namespaces()
            summary["resources"]["pods"] = len(pods.items)
            
            services = self.v1.list_service_for_all_namespaces()
            summary["resources"]["services"] = len(services.items)
            
            deployments = self.apps_v1.list_deployment_for_all_namespaces()
            summary["resources"]["deployments"] = len(deployments.items)
            
            namespaces = self.v1.list_namespace()
            summary["resources"]["namespaces"] = len(namespaces.items)
            
            configmaps = self.v1.list_config_map_for_all_namespaces()
            summary["resources"]["configmaps"] = len(configmaps.items)
            
            secrets = self.v1.list_secret_for_all_namespaces()
            summary["resources"]["secrets"] = len(secrets.items)
            
        except ApiException as e:
            summary["error"] = str(e)
            
        return summary
