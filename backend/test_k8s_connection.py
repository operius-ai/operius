#!/usr/bin/env python3
"""
Simple test script to verify Kubernetes connection without heavy dependencies.
"""

import subprocess
import json
import sys


def test_kubectl_connection():
    """Test if kubectl can connect to the cluster."""
    print("🔍 Testing kubectl connection...")
    
    try:
        # Test basic connection
        result = subprocess.run(['kubectl', 'cluster-info'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ kubectl connection successful")
            print(f"📊 Cluster info:\n{result.stdout}")
            return True
        else:
            print(f"❌ kubectl connection failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ kubectl connection timed out")
        return False
    except FileNotFoundError:
        print("❌ kubectl not found - please install kubectl")
        return False


def get_cluster_resources():
    """Get basic cluster resource counts."""
    print("\n📦 Getting cluster resources...")
    
    resources = {
        'pods': 'kubectl get pods --all-namespaces --no-headers',
        'services': 'kubectl get services --all-namespaces --no-headers', 
        'deployments': 'kubectl get deployments --all-namespaces --no-headers',
        'namespaces': 'kubectl get namespaces --no-headers'
    }
    
    resource_counts = {}
    
    for resource_type, command in resources.items():
        try:
            result = subprocess.run(command.split(), 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = [line for line in result.stdout.strip().split('\n') if line.strip()]
                count = len(lines)
                resource_counts[resource_type] = count
                print(f"   • {resource_type}: {count}")
            else:
                resource_counts[resource_type] = 0
                print(f"   • {resource_type}: 0 (error: {result.stderr.strip()})")
                
        except subprocess.TimeoutExpired:
            resource_counts[resource_type] = 0
            print(f"   • {resource_type}: 0 (timeout)")
    
    return resource_counts


def test_minikube_status():
    """Check minikube status."""
    print("\n🚀 Checking minikube status...")
    
    try:
        result = subprocess.run(['minikube', 'status'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Minikube is running")
            print(f"📊 Status:\n{result.stdout}")
            return True
        else:
            print(f"❌ Minikube status check failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Minikube status check timed out")
        return False
    except FileNotFoundError:
        print("❌ minikube not found")
        return False


def main():
    """Run all tests."""
    print("🧪 Operius Kubernetes Connection Test")
    print("=" * 50)
    
    # Test minikube
    minikube_ok = test_minikube_status()
    
    # Test kubectl
    kubectl_ok = test_kubectl_connection()
    
    if kubectl_ok:
        # Get resource counts
        resources = get_cluster_resources()
        
        print(f"\n📈 Summary:")
        print(f"   Total resources: {sum(resources.values())}")
        
        if sum(resources.values()) > 0:
            print("✅ Cluster has resources - ready for ingestion!")
        else:
            print("⚠️  Cluster appears empty")
    
    print(f"\n🎯 Test Results:")
    print(f"   • Minikube: {'✅' if minikube_ok else '❌'}")
    print(f"   • kubectl: {'✅' if kubectl_ok else '❌'}")
    
    if minikube_ok and kubectl_ok:
        print("\n🚀 System is ready for the full demo!")
        print("💡 Next steps:")
        print("   1. Install Python dependencies: pip install kubernetes chromadb sentence-transformers")
        print("   2. Run the full demo: python demo.py")
    else:
        print("\n❌ System not ready - please fix the issues above")
        
    return minikube_ok and kubectl_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
