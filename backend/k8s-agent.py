class ClusterStateManager:
    def __init__(self):
        self.k8s_client = kubernetes.client.ApiClient()
        self.vector_store = VectorStore()
    
    async def get_enriched_state(self, query):
        # Real-time data from K8s API
        live_state = await self.k8s_client.list_pods()
        
        # Historical context from vector DB  
        context = await self.vector_store.similarity_search(query)
        
        # Combine for richer understanding
        return self.merge_live_and_historical(live_state, context)

# Core agent architecture
class KubernetesAgent:
    def __init__(self):
        self.k8s_client = KubernetesClient()
        self.vector_store = PostgresVectorStore()
        self.llm_router = LLMRouter()
        self.memory = ConversationMemory()
    
    async def analyze_incident(self, alert):
        # 1. Get real-time cluster state
        cluster_state = await self.k8s_client.get_current_state()
        
        # 2. Query historical context
        similar_incidents = await self.vector_store.find_similar(
            alert.description, 
            filter_by_cluster=alert.cluster_id
        )
        
        # 3. Route to appropriate LLM
        analysis = await self.llm_router.analyze(
            current_state=cluster_state,
            historical_context=similar_incidents,
            task_type="incident_analysis"
        )
        
        return analysis


