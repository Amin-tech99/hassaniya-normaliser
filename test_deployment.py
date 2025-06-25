#!/usr/bin/env python3
"""Test the deployed normalizer service using built-in modules."""

import urllib.request
import urllib.parse
import json

def test_deployment():
    base_url = "https://hassaniya-normaliser.onrender.com"
    
    print("Testing Hassaniya Normalizer Deployment")
    print("=" * 40)
    
    # Test health check
    try:
        with urllib.request.urlopen(f"{base_url}/healthz", timeout=10) as response:
            status_code = response.getcode()
            content = response.read().decode('utf-8')
            print(f"Health check - Status: {status_code}")
            if status_code == 200:
                print(f"Health check - Response: {content}")
            else:
                print(f"Health check - Error: {content}")
    except Exception as e:
        print(f"Health check - Failed: {e}")
    
    print()
    
    # Test normalize endpoint
    try:
        test_text = "قال الرجل"
        data = json.dumps({"text": test_text}).encode('utf-8')
        req = urllib.request.Request(
            f"{base_url}/api/normalize",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.getcode()
            content = response.read().decode('utf-8')
            print(f"Normalize test - Status: {status_code}")
            if status_code == 200:
                result = json.loads(content)
                print(f"Normalize test - Input: {test_text}")
                print(f"Normalize test - Output: {result.get('normalized_text', 'N/A')}")
                print(f"Normalize test - Full response: {result}")
            else:
                print(f"Normalize test - Error: {content}")
    except Exception as e:
        print(f"Normalize test - Failed: {e}")
    
    print()
    
    # Test stats endpoint
    try:
        with urllib.request.urlopen(f"{base_url}/api/stats", timeout=10) as response:
            status_code = response.getcode()
            content = response.read().decode('utf-8')
            print(f"Stats test - Status: {status_code}")
            if status_code == 200:
                stats = json.loads(content)
                print(f"Stats test - Response: {stats}")
            else:
                print(f"Stats test - Error: {content}")
    except Exception as e:
        print(f"Stats test - Failed: {e}")

if __name__ == "__main__":
    test_deployment()