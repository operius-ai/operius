#!/usr/bin/env python3
"""
Interactive Chat Interface for Operius Knowledge Base

Talk to your Kubernetes cluster using natural language!
This script combines vector search with AI responses for conversational interaction.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add paths for imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "google-adk" / "src"))

from backend.vector_store import ChromaVectorStore
from backend.search_agent import SearchAgent
from adk_agent.agents.core_agent import create_core_agent


class KubernetesChat:
    """Interactive chat interface for Kubernetes knowledge base."""
    
    def __init__(self):
        """Initialize the chat interface."""
        self.vector_store = None
        self.search_agent = None
        self.ai_agent = None
        self.conversation_history = []
        
    async def initialize(self):
        """Initialize all components."""
        print("🔧 Initializing Kubernetes Chat Interface...")
        
        # Initialize vector store (using the same one from demo)
        self.vector_store = ChromaVectorStore(
            persist_directory="./chroma_db",
            collection_name="operius_demo"
        )
        
        # Initialize search agent
        self.search_agent = SearchAgent(self.vector_store)
        
        # Initialize AI agent
        try:
            print("🔍 Pre-initialization check:")
            print(f"   • API Key set: {'Yes' if os.getenv('OPENROUTER_API_KEY') else 'No'}")
            print(f"   • API Key length: {len(os.getenv('OPENROUTER_API_KEY', ''))}")
            
            config = {"model": "anthropic/claude-3.5-sonnet"}
            print(f"   • Creating agent with config: {config}")
            self.ai_agent = create_core_agent(config)
            print("✅ AI agent initialized successfully")
            
            # Test the agent with a simple query
            test_response = self.ai_agent.run("You are a test assistant.", "Reply with 'OK'")
            print(f"✅ AI agent test successful: {test_response}")
            
        except Exception as e:
            print(f"⚠️  AI agent failed: {e}")
            print(f"🔍 Debug info:")
            print(f"   • API Key set: {'Yes' if os.getenv('OPENROUTER_API_KEY') else 'No'}")
            print(f"   • API Key length: {len(os.getenv('OPENROUTER_API_KEY', ''))}")
            import traceback
            traceback.print_exc()
            self.ai_agent = None
        
        # Check if knowledge base has data
        stats = self.vector_store.get_collection_stats()
        if stats['total_documents'] == 0:
            print("❌ No data in knowledge base. Run the demo first: python -m backend.demo")
            return False
            
        print(f"✅ Knowledge base loaded: {stats['total_documents']} documents")
        print(f"📊 Resource types: {list(stats.get('kubernetes_kinds', {}).keys())}")
        return True
    
    def create_system_prompt(self, search_results: Dict[str, Any]) -> str:
        """Create system prompt with search context."""
        context = ""
        if search_results.get('results'):
            context = "KUBERNETES CLUSTER CONTEXT:\n"
            for i, result in enumerate(search_results['results'][:5], 1):
                metadata = result.get('metadata', {})
                context += f"{i}. {metadata.get('kind', 'Unknown')} '{metadata.get('name', 'Unknown')}' "
                context += f"in namespace '{metadata.get('namespace', 'default')}'\n"
                if 'content' in result:
                    context += f"   Details: {result['content'][:200]}...\n"
            context += "\n"
        
        return f"""You are a helpful Kubernetes expert assistant. You have access to information about a Kubernetes cluster.

{context}

Instructions:
- Answer questions about Kubernetes resources based on the provided context
- Be concise but informative
- If the context doesn't contain relevant information, say so clearly
- Use emojis to make responses friendly and easy to read
- Focus on practical, actionable information
- If asked about resources not in the context, suggest what commands or searches might help

Remember: You're helping someone understand and manage their Kubernetes cluster."""

    async def search_knowledge_base(self, query: str) -> Dict[str, Any]:
        """Search the knowledge base for relevant information."""
        # Analyze query intent
        intent = await self.search_agent.analyze_query_intent(query)
        
        # Perform appropriate search
        if 'kubernetes' in intent.get('detected_intents', []):
            # Use Kubernetes-specific search if intent detected
            suggested_filters = intent.get('suggested_filters', {})
            results = await self.search_agent.search_kubernetes(
                query,
                resource_kind=suggested_filters.get('kind'),
                namespace=suggested_filters.get('namespace'),
                max_results=10
            )
        else:
            # General search
            results = await self.search_agent.search(query, max_results=10)
        
        return results
    
    async def get_ai_response(self, user_query: str, search_results: Dict[str, Any]) -> str:
        """Get AI response based on search results."""
        if not self.ai_agent:
            # Fallback to formatted search results
            if search_results.get('results'):
                formatted = self.search_agent.format_search_results(search_results['results'][:3])
                return f"🔍 Here's what I found in your cluster:\n\n{formatted}"
            else:
                return "🤔 I couldn't find any relevant resources for your query."
        
        try:
            system_prompt = self.create_system_prompt(search_results)
            response = self.ai_agent.run(system_prompt, user_query)
            return response
        except Exception as e:
            # Fallback if AI fails
            if search_results.get('results'):
                formatted = self.search_agent.format_search_results(search_results['results'][:3])
                return f"🔍 Here's what I found (AI unavailable):\n\n{formatted}"
            else:
                return f"❌ AI response failed: {e}"
    
    async def handle_query(self, user_input: str) -> str:
        """Handle a user query end-to-end."""
        # Search knowledge base
        search_results = await self.search_knowledge_base(user_input)
        
        # Get AI response
        response = await self.get_ai_response(user_input, search_results)
        
        # Store in conversation history
        self.conversation_history.append({
            'user': user_input,
            'assistant': response,
            'search_results_count': len(search_results.get('results', []))
        })
        
        return response
    
    def print_help(self):
        """Print help information."""
        print("""
💬 Kubernetes Chat Commands:
   • Ask any question about your cluster: "What pods are running?"
   • Get resource information: "Show me services in kube-system"
   • Find specific resources: "Find deployments with issues"
   • General queries: "What's the status of my cluster?"
   
🔧 Special Commands:
   • /help - Show this help
   • /stats - Show knowledge base statistics  
   • /history - Show conversation history
   • /clear - Clear conversation history
   • /quit or /exit - Exit the chat
        """)
    
    async def run_interactive(self):
        """Run the interactive chat loop."""
        if not await self.initialize():
            return
        
        print("\n Chat with knowledge base")
        print("💬 Ask me anything about your Kubernetes cluster.")
        print("Type '/help' for commands or '/quit' to exit.\n")
        
        while True:
            try:
                # Get user input
                user_input = input("🤖 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['/quit', '/exit']:
                    print("👋")
                    break
                elif user_input.lower() == '/help':
                    self.print_help()
                    continue
                elif user_input.lower() == '/stats':
                    stats = self.vector_store.get_collection_stats()
                    print(f"\n📊 Knowledge Base Stats:")
                    print(f"   • Total documents: {stats['total_documents']}")
                    print(f"   • Resource types: {list(stats.get('kubernetes_kinds', {}).keys())}")
                    print(f"   • Embedding model: {stats.get('embedding_model', 'Unknown')}")
                    continue
                elif user_input.lower() == '/history':
                    print(f"\n📜 Conversation History ({len(self.conversation_history)} exchanges):")
                    for i, exchange in enumerate(self.conversation_history[-5:], 1):
                        print(f"   {i}. Q: {exchange['user'][:50]}...")
                        print(f"      A: {exchange['assistant'][:100]}...")
                    continue
                elif user_input.lower() == '/clear':
                    self.conversation_history.clear()
                    print("🗑️  Conversation history cleared.")
                    continue
                
                # Handle regular query
                print("🔍 Searching knowledge base...")
                response = await self.handle_query(user_input)
                print(f"\n🤖 Assistant: {response}\n")
                
            except KeyboardInterrupt:
                print("\n👋 Chat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


async def main():
    """Main entry point."""
    chat = KubernetesChat()
    await chat.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())
