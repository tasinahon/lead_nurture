import requests

# Test different request methods and URLs
base_url = "https://linkedin-scraper-f9gvanhghvcqccdu.eastus-01.azurewebsites.net/"

payload = {
    "profile_url": "https://www.linkedin.com/in/shahrukhrydwan/",
    "save_to_file": False
}
headers = {
    "accept": "application/json",
    "Content-Type": "application/json"
}

# Test 1: Health check (should work)
print("=== Testing Health Check ===")
response = requests.get(f"{base_url}/")
print(f"GET /: {response.status_code}")
if response.status_code == 200:
    print("Health check works!")
else:
    print(f"Error: {response.text}")

print("\n=== Testing API Status ===")
response = requests.get(f"{base_url}/api/status")
print(f"GET /api/status: {response.status_code}")
if response.status_code == 200:
    print("API Status works!")
else:
    print(f"Error: {response.text}")

print("\n=== Testing Scrape Endpoint ===")
# Test different variations
test_urls = [
    f"{base_url}/api/scrape",
    f"{base_url}/api/scrape/",
]

for url in test_urls:
    print(f"Trying POST to: {url}")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("SUCCESS!")
            print(response.text)
            break
        else:
            print(f"Error: {response.text[:200]}...")
    except requests.exceptions.Timeout:
        print("Request timed out - app might be processing")
    except Exception as e:
        print(f"Exception: {e}")
    print("-" * 50)