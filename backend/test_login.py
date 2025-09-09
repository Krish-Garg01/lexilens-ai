import requests

# Test login
response = requests.post("http://localhost:8000/token", data={"username": "test@example.com", "password": "test123"})
print("Status:", response.status_code)
print("Response:", response.json())
