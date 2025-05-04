#!/usr/bin/env python3
"""
Test the login endpoint directly
"""
import requests
import sys
import json

def test_login(username, password, verbose=True):
    """
    Test login with the given credentials
    """
    base_url = "http://localhost:8000"
    login_url = f"{base_url}/api/auth/token"
    health_url = f"{base_url}/"
    
    # First check if server is up
    try:
        health_response = requests.get(health_url)
        print(f"Server health check: {health_response.status_code}")
        if verbose:
            print(f"Health response: {health_response.text}")
    except Exception as e:
        print(f"Server health check failed: {str(e)}")
        return False
    
    # Try login - Use proper form data for OAuth2
    print(f"Attempting login for user: {username}")
    try:
        # Enable verbose error details
        session = requests.Session()
        session.trust_env = False
        
        # Use proper form data encoding for OAuth2
        response = session.post(
            login_url, 
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        print(f"Status code: {response.status_code}")
        
        try:
            json_resp = response.json()
            print(f"Response JSON: {json.dumps(json_resp, indent=2)}")
        except:
            print(f"Response text: {response.text}")
        
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False

def test_register(email, username, password, full_name):
    """Test user registration"""
    url = "http://localhost:8000/api/auth/register"
    data = {
        "email": email,
        "username": username,
        "password": password,
        "full_name": full_name
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Attempting to register user: {username}")
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"Registration status code: {response.status_code}")
        
        try:
            json_resp = response.json()
            print(f"Registration response: {json.dumps(json_resp, indent=2)}")
        except:
            print(f"Registration response text: {response.text}")
        
        return response.status_code in [200, 201, 409]  # 409 is conflict, means user exists
    except Exception as e:
        print(f"Registration exception: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_login.py <username> <password> [<email> <full_name>]")
        print("Examples:")
        print("  python test_login.py testuser Password123!@#")
        print("  python test_login.py newuser Password123!@# newuser@example.com 'New User'")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    # If email and full_name are provided, try registration first
    if len(sys.argv) >= 5:
        email = sys.argv[3]
        full_name = sys.argv[4]
        
        register_success = test_register(email, username, password, full_name)
        print(f"Registration successful: {register_success}")
        
        if not register_success:
            print("Registration failed, still attempting login...")
    
    # Now try login
    login_success = test_login(username, password)
    print(f"Login successful: {login_success}")
    sys.exit(0 if login_success else 1) 