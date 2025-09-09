import requests

# Register test user
response = requests.post("http://localhost:8000/register", params={"email": "test@example.com", "password": "test123"})
print("Register Status:", response.status_code)
print("Register Response:", response.text)

# Then login
response = requests.post("http://localhost:8000/token", data={"username": "test@example.com", "password": "test123"})
print("Login Status:", response.status_code)
print("Login Response:", response.json() if response.status_code == 200 else response.text)
