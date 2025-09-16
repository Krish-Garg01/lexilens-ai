import urllib.request
import json

try:
    with urllib.request.urlopen('http://localhost:8000/health') as response:
        data = json.loads(response.read().decode())
        print(f"Status Code: {response.getcode()}")
        print(f"Response: {data}")
except Exception as e:
    print(f"Error: {e}")
