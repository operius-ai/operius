#!/usr/bin/env python3
"""
Add GitHub Repository to Knowledge Base

This script fetches a GitHub repository's files and adds them to the vector store
alongside the existing Kubernetes data.
"""

import asyncio
import sys
import os
import base64
from pathlib import Path
from typing import List, Dict, Any
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add paths for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.vector_store import ChromaVectorStore
from backend.ingestion_pipeline import IngestionPipeline


class SimpleGitHubSource:
    """Simple GitHub repository fetcher for our knowledge base."""
    
    def __init__(self, repo_name: str, github_token: str = None):
        self.repo_name = repo_name  # format: "owner/repo"
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "operius-knowledge-base"
        }
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        return headers
    
    async def _get_file_content(self, client: httpx.AsyncClient, file_path: str, branch: str = "main") -> str:
        """Get file content from GitHub API."""
        url = f"{self.base_url}/repos/{self.repo_name}/contents/{file_path}"
        params = {"ref": branch}
        
        response = await client.get(url, headers=self._get_headers(), params=params)
        response.raise_for_status()
        
        file_data = response.json()
        if file_data.get("encoding") == "base64":
            content = base64.b64decode(file_data["content"]).decode("utf-8", errors="ignore")
            return content
        return ""
    
    async def _is_text_file(self, file_path: str) -> bool:
        """Check if file is likely a text file based on extension."""
        text_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
            '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.clj',
            '.md', '.txt', '.yml', '.yaml', '.json', '.xml', '.html', '.css', '.scss',
            '.sql', '.sh', '.bash', '.dockerfile', '.gitignore', '.env.example',
            '.toml', '.ini', '.cfg', '.conf', '.lock'
        }
        
        # Files without extensions that are usually text
        text_filenames = {
            'README', 'LICENSE', 'CHANGELOG', 'CONTRIBUTING', 'Dockerfile',
            'Makefile', 'requirements.txt', 'package.json', 'Cargo.toml'
        }
        
        file_path_lower = file_path.lower()
        filename = Path(file_path).name
        
        # Check extension
        if Path(file_path).suffix.lower() in text_extensions:
            return True
            
        # Check filename
        if filename in text_filenames:
            return True
            
        return False
    
    async def _get_repository_tree(self, client: httpx.AsyncClient, branch: str = "main") -> List[Dict[str, Any]]:
        """Get all files in the repository."""
        url = f"{self.base_url}/repos/{self.repo_name}/git/trees/{branch}"
        params = {"recursive": "1"}
        
        response = await client.get(url, headers=self._get_headers(), params=params)
        response.raise_for_status()
        
        tree_data = response.json()
        return tree_data.get("tree", [])
    
    async def fetch_repository_files(self, max_files: int = 50) -> List[Dict[str, Any]]:
        """Fetch repository files and return as documents."""
        documents = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Get repository info
                repo_url = f"{self.base_url}/repos/{self.repo_name}"
                repo_response = await client.get(repo_url, headers=self._get_headers())
                repo_response.raise_for_status()
                repo_data = repo_response.json()
                
                print(f"📁 Repository: {repo_data['full_name']}")
                print(f"📝 Description: {repo_data.get('description', 'No description')}")
                print(f"🌟 Stars: {repo_data.get('stargazers_count', 0)}")
                print(f"🍴 Forks: {repo_data.get('forks_count', 0)}")
                
                # Get default branch
                default_branch = repo_data.get("default_branch", "main")
                
                # Get file tree
                tree = await self._get_repository_tree(client, default_branch)
                
                # Filter for text files only
                text_files = [
                    item for item in tree 
                    if item["type"] == "blob" and await self._is_text_file(item["path"])
                ]
                
                print(f"🔍 Found {len(text_files)} text files, processing first {max_files}...")
                
                # Process files (limit to avoid rate limits)
                for i, file_item in enumerate(text_files[:max_files]):
                    file_path = file_item["path"]
                    print(f"  📄 Processing {file_path}...")
                    
                    try:
                        content = await self._get_file_content(client, file_path, default_branch)
                        
                        if content.strip():  # Only add non-empty files
                            # Create document
                            document = {
                                "content": content,
                                "metadata": {
                                    "source": "github",
                                    "repo_name": self.repo_name,
                                    "file_path": file_path,
                                    "file_name": Path(file_path).name,
                                    "file_extension": Path(file_path).suffix,
                                    "repo_description": repo_data.get('description', ''),
                                    "repo_language": repo_data.get('language', ''),
                                    "repo_stars": repo_data.get('stargazers_count', 0),
                                    "url": f"https://github.com/{self.repo_name}/blob/{default_branch}/{file_path}"
                                }
                            }
                            documents.append(document)
                            
                    except Exception as e:
                        print(f"    ⚠️  Error processing {file_path}: {e}")
                        continue
                
                print(f"✅ Successfully processed {len(documents)} files")
                return documents
                
            except Exception as e:
                print(f"❌ Error fetching repository: {e}")
                return []


async def add_github_repo_to_knowledge_base(repo_name: str, github_token: str = None):
    """Add a GitHub repository to the existing knowledge base."""
    
    print(f"🚀 Adding GitHub repository '{repo_name}' to knowledge base...")
    
    # Initialize vector store (same as demo)
    vector_store = ChromaVectorStore(
        persist_directory="./chroma_db",
        collection_name="operius_demo"
    )
    
    # Get current stats
    initial_stats = vector_store.get_collection_stats()
    print(f"📊 Current knowledge base: {initial_stats['total_documents']} documents")
    
    # Fetch GitHub repository
    github_source = SimpleGitHubSource(repo_name, github_token)
    documents = await github_source.fetch_repository_files(max_files=30)
    
    if not documents:
        print("❌ No documents to add")
        return
    
    # Initialize ingestion pipeline
    pipeline = IngestionPipeline(vector_store)
    
    # Add documents to vector store
    print(f"📥 Adding {len(documents)} documents to vector store...")
    await pipeline.process_documents(documents, source_name="github")
    
    # Get final stats
    final_stats = vector_store.get_collection_stats()
    added_docs = final_stats['total_documents'] - initial_stats['total_documents']
    
    print(f"✅ Successfully added {added_docs} documents!")
    print(f"📚 Total documents in knowledge base: {final_stats['total_documents']}")
    print(f"📂 Data sources: {final_stats.get('sources', [])}")
    
    return final_stats


async def main():
    """Main function to add a GitHub repository."""
    
    # Example repositories (you can change these)
    example_repos = [
        "kubernetes/kubernetes",  # Large repo - will only process first 30 files
        "microsoft/vscode",       # Another large repo
        "facebook/react",         # Popular frontend framework
        "torvalds/linux",         # Linux kernel (very large)
        "python/cpython",         # Python source code
    ]
    
    print("🔧 Available example repositories:")
    for i, repo in enumerate(example_repos, 1):
        print(f"  {i}. {repo}")
    
    # Get user input
    try:
        choice = input("\nEnter repository name (owner/repo) or number from list above: ").strip()
        
        # Check if it's a number
        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(example_repos):
                repo_name = example_repos[choice_num - 1]
            else:
                print("❌ Invalid choice number")
                return
        else:
            repo_name = choice
            
        if "/" not in repo_name:
            print("❌ Repository name must be in format 'owner/repo'")
            return
            
        print(f"\n🎯 Selected repository: {repo_name}")
        
        # Check for GitHub token
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            print("⚠️  No GITHUB_TOKEN found in environment. Using unauthenticated requests (rate limited).")
            print("   Add GITHUB_TOKEN to your .env file for higher rate limits.")
        else:
            print("✅ GitHub token found - using authenticated requests")
        
        # Add repository to knowledge base
        await add_github_repo_to_knowledge_base(repo_name, github_token)
        
        print(f"\n🎉 Repository '{repo_name}' has been added to your knowledge base!")
        print("💡 You can now ask questions about this repository in the chat interface:")
        print("   python -m backend.chat")
        
    except KeyboardInterrupt:
        print("\n👋 Cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
