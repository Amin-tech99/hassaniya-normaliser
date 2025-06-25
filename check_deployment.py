#!/usr/bin/env python3
import urllib.request
import urllib.parse
import json

def test_deployment():
    base_url = "https://hassaniya-normaliser.onrender.com"
    
    print("Testing Hassaniya Normalizer Deployment")
    print("=" * 40)
    
    # Test health check
    try:
        with urllib.request.urlopen(f"{base_url}/healthz") as response:
            print(f"Health check - Status: {response.status}")
            if response.status == 200:
                data = json.loads(response.read().decode())
                print(f"Health check - Response: {data}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    print()
    
    # Test normalize endpoint
    try:
        test_text = "قال الرجل"
        data = json.dumps({"text": test_text, "show_diff": True}).encode('utf-8')
        req = urllib.request.Request(
            f"{base_url}/api/normalize",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req) as response:
            print(f"Normalize test - Status: {response.status}")
            if response.status == 200:
                result = json.loads(response.read().decode())
                print(f"Normalize test - Input: {test_text}")
                print(f"Normalize test - Output: {result.get('normalized', 'N/A')}")
                print(f"Normalize test - Changes: {len(result.get('changes', []))}")
                if result.get('original') == result.get('normalized'):
                    print("⚠️  WARNING: No normalization occurred - likely using fallback function")
                else:
                    print("✅ Normalization working correctly")
    except Exception as e:
        print(f"Normalize test failed: {e}")
    
    print()
    
    # Test debug endpoint
    try:
        with urllib.request.urlopen(f"{base_url}/api/debug/data-files") as response:
            print(f"Debug test - Status: {response.status}")
            if response.status == 200:
                debug_data = json.loads(response.read().decode())
                print(f"Debug test - Normalizer stats: {debug_data.get('normalizer_stats', {})}")
                
                # Check if data files are accessible
                data_files = debug_data.get('data_files_status', {})
                for filename, status in data_files.items():
                    if status.get('found') and status.get('exists'):
                        print(f"✅ {filename}: Found and accessible")
                    else:
                        print(f"❌ {filename}: {status.get('error', 'Not found or inaccessible')}")
    except Exception as e:
        print(f"Debug test failed: {e}")

if __name__ == "__main__":
    test_deployment()