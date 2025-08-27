#!/usr/bin/env python3
"""
Simple GitHub Repository Adder for Knowledge Base

This script fetches a GitHub repository's files and adds them to the vector store
without complex imports that cause conflicts.
"""

import asyncio
import os
import base64
import json
from pathlib import Path
from typing import List, Dict, Any
import httpx
from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()


class SimpleGitHubAdder:
    """Simple GitHub repository fetcher for our knowledge base."""
    
    def __init__(self, repo_name: str, github_token: str = None):
        self.repo_name = repo_name  # format: "owner/repo"
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        
        # Initialize vector store directly
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.chroma_client.get_collection("operius_demo")
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
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
    
    def _get_current_stats(self) -> Dict[str, Any]:
        """Get current collection statistics."""
        try:
            count = self.collection.count()
            return {"total_documents": count}
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {"total_documents": 0}
    
    async def add_repository_to_knowledge_base(self, max_files: int = 30) -> Dict[str, Any]:
        """Add GitHub repository to the knowledge base."""
        
        print(f"🚀 Adding GitHub repository '{self.repo_name}' to knowledge base...")
        
        # Get current stats
        initial_stats = self._get_current_stats()
        print(f"📊 Current knowledge base: {initial_stats['total_documents']} documents")
        
        documents_added = 0
        
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
                
                # Prepare batch data for ChromaDB
                documents = []
                metadatas = []
                ids = []
                
                # Process files (limit to avoid rate limits)
                for i, file_item in enumerate(text_files[:max_files]):
                    file_path = file_item["path"]
                    print(f"  📄 Processing {file_path}...")
                    
                    try:
                        content = await self._get_file_content(client, file_path, default_branch)
                        
                        if content.strip():  # Only add non-empty files
                            # Create unique ID
                            doc_id = f"github_{self.repo_name.replace('/', '_')}_{file_path.replace('/', '_')}"
                            
                            # Prepare document content
                            document_text = f"File: {file_path}\nRepository: {self.repo_name}\n\n{content}"
                            
                            # Prepare metadata (ensure no None values)
                            metadata = {
                                "source": "github",
                                "repo_name": str(self.repo_name),
                                "file_path": str(file_path),
                                "file_name": str(Path(file_path).name),
                                "file_extension": str(Path(file_path).suffix),
                                "repo_description": str(repo_data.get('description') or ''),
                                "repo_language": str(repo_data.get('language') or ''),
                                "repo_stars": int(repo_data.get('stargazers_count') or 0),
                                "url": f"https://github.com/{self.repo_name}/blob/{default_branch}/{file_path}"
                            }
                            
                            documents.append(document_text)
                            metadatas.append(metadata)
                            ids.append(doc_id)
                            documents_added += 1
                            
                    except Exception as e:
                        print(f"    ⚠️  Error processing {file_path}: {e}")
                        continue
                
                # Add documents to ChromaDB in batch
                if documents:
                    print(f"📥 Adding {len(documents)} documents to vector store...")
                    
                    # Generate embeddings
                    embeddings = self.embedding_model.encode(documents).tolist()
                    
                    # Add to collection
                    self.collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids,
                        embeddings=embeddings
                    )
                    
                    print(f"✅ Successfully added {documents_added} documents!")
                else:
                    print("❌ No documents to add")
                
                # Get final stats
                final_stats = self._get_current_stats()
                total_added = final_stats['total_documents'] - initial_stats['total_documents']
                
                print(f"📚 Total documents in knowledge base: {final_stats['total_documents']}")
                print(f"➕ Documents added in this session: {total_added}")
                
                return {
                    "repo_name": self.repo_name,
                    "documents_processed": documents_added,
                    "total_documents": final_stats['total_documents']
                }
                
            except Exception as e:
                print(f"❌ Error fetching repository: {e}")
                return {"error": str(e)}


async def main():
    """Main function to add a GitHub repository."""
    
    # Get user input
    try:
        print("🔧 Add GitHub Repository to Knowledge Base")
        print("Enter a GitHub repository URL or owner/repo format")
        
        user_input = input("\nEnter GitHub repository URL or owner/repo: ").strip()
        
        # Parse the input to extract owner/repo
        if user_input.startswith("https://github.com/"):
            # Extract from URL
            repo_path = user_input.replace("https://github.com/", "").rstrip("/")
            repo_name = repo_path
        elif user_input.startswith("github.com/"):
            # Handle github.com/ format
            repo_name = user_input.replace("github.com/", "").rstrip("/")
        else:
            # Assume it's already in owner/repo format
            repo_name = user_input
            
        if "/" not in repo_name:
            print("❌ Repository must be in format 'owner/repo' or a valid GitHub URL")
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
        adder = SimpleGitHubAdder(repo_name, github_token)
        result = await adder.add_repository_to_knowledge_base(max_files=25)
        
        if "error" not in result:
            print(f"\n🎉 Repository '{repo_name}' has been added to your knowledge base!")
            print("💡 You can now ask questions about this repository in the chat interface:")
            print("   python -m backend.chat")
        else:
            print(f"❌ Failed to add repository: {result['error']}")
        
    except KeyboardInterrupt:
        print("\n👋 Cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
