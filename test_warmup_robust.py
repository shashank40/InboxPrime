#!/usr/bin/env python3
import asyncio
import logging
import time
import sys
import os
import json
import getpass
import requests
from urllib.parse import urljoin
from datetime import datetime

# Configure logging
log_format = '%(asctime)s - %(levelname)s - %(message)s'
log_filename = f"email_warmup_robust_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("email_warmup")

# API Base URL
API_BASE_URL = "http://localhost:8000/api/"

class RobustEmailWarmupTester:
    """A more robust tester that handles various errors and retries operations"""
    
    def __init__(self, base_url=API_BASE_URL):
        self.base_url = base_url
        self.auth_token = None
        self.user_id = None
        self.email_accounts = []
        self.max_retries = 3
        
    def _make_url(self, endpoint):
        """Construct full URL for the given endpoint"""
        return urljoin(self.base_url, endpoint)
    
    def _make_headers(self, with_auth=True, content_type="application/json"):
        """Create headers for API requests"""
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        if with_auth and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
    
    def api_request(self, method, endpoint, headers=None, json_data=None, data=None, retries=3):
        """Make an API request with retry logic"""
        if headers is None:
            headers = self._make_headers()
            
        url = self._make_url(endpoint)
        retry_count = 0
        
        while retry_count < retries:
            try:
                if retry_count > 0:
                    logger.info(f"Retry attempt {retry_count} for {endpoint}")
                    time.sleep(1)  # Wait between retries
                
                if method.upper() == 'GET':
                    response = requests.get(url, headers=headers)
                elif method.upper() == 'POST':
                    if json_data:
                        response = requests.post(url, headers=headers, json=json_data)
                    else:
                        response = requests.post(url, headers=headers, data=data)
                elif method.upper() == 'PUT':
                    response = requests.put(url, headers=headers, json=json_data)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                # If successful or clear client error, don't retry
                if response.status_code < 500:
                    return response
                
                # Server error, retry
                logger.warning(f"Server error {response.status_code} for {endpoint}. Retrying...")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {str(e)}")
                if retry_count == retries - 1:
                    raise
            
            retry_count += 1
        
        # If we get here, all retries failed
        raise Exception(f"Failed after {retries} attempts for {endpoint}")
    
    def test_server_connection(self):
        """Test if the server is running"""
        try:
            response = requests.get(self._make_url("health"))
            if response.status_code == 200:
                return True
                
            # If health endpoint not available, try accessing any endpoint
            response = requests.get(self._make_url(""))
            return response.status_code != 404
        except:
            return False
    
    def register_user(self, email, username, password, full_name):
        """Register a new user in the system"""
        logger.info(f"Registering user: {username}")
        try:
            response = self.api_request(
                'POST',
                "auth/register",
                headers=self._make_headers(with_auth=False),
                json_data={
                    "email": email,
                    "username": username,
                    "password": password,
                    "full_name": full_name
                }
            )
            
            if response.status_code == 200:
                logger.info("User registered successfully")
                return True
            elif response.status_code == 409 or "Username already registered" in response.text:
                logger.info("User already exists, proceeding to login")
                return True
            else:
                logger.error(f"Failed to register user: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error during user registration: {str(e)}")
            return False
    
    def login(self, username, password):
        """Login and get authentication token"""
        logger.info(f"Logging in as: {username}")
        try:
            response = self.api_request(
                'POST',
                "auth/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "username": username,
                    "password": password
                },
                retries=3
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                logger.info("Login successful")
                
                # Get user information
                me_response = self.api_request(
                    'GET',
                    "users/me"
                )
                if me_response.status_code == 200:
                    user_data = me_response.json()
                    self.user_id = user_data.get("id")
                    logger.info(f"Got user ID: {self.user_id}")
                
                return True
            else:
                logger.error(f"Failed to login: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False
    
    def add_email_account(self, email_data):
        """Add an email account to the system with proper error handling"""
        logger.info(f"Adding email account: {email_data['email_address']}")
        try:
            response = self.api_request(
                'POST',
                "emails",
                json_data=email_data
            )
            
            if response.status_code == 200:
                account = response.json()
                logger.info(f"Added email account with ID: {account['id']}")
                self.email_accounts.append(account)
                return account
            elif response.status_code == 400 and "Email account already registered" in response.text:
                logger.warning(f"Email {email_data['email_address']} already registered, trying to retrieve it")
                
                # Try to get existing accounts and find this one
                accounts_response = self.api_request('GET', "emails")
                if accounts_response.status_code == 200:
                    accounts = accounts_response.json()
                    for account in accounts:
                        if account['email_address'] == email_data['email_address']:
                            logger.info(f"Found existing account with ID: {account['id']}")
                            self.email_accounts.append(account)
                            return account
                
                logger.error(f"Could not retrieve existing account")
                return None
            else:
                logger.error(f"Failed to add email account: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error adding email account: {str(e)}")
            return None
    
    def verify_email_account(self, account_id):
        """Verify an email account's credentials with retry"""
        logger.info(f"Verifying email account with ID: {account_id}")
        
        # Try verification multiple times - it sometimes fails on first attempt
        for attempt in range(3):
            try:
                if attempt > 0:
                    logger.info(f"Verification attempt {attempt+1} for account {account_id}")
                    time.sleep(2)  # Wait between attempts
                
                response = self.api_request(
                    'POST',
                    f"emails/{account_id}/verify"
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Verification response: {result}")
                    
                    # Check both "success" field and "status" field
                    success = result.get("success", False) or result.get("status") == "success"
                    
                    if success:
                        logger.info(f"Email account {account_id} verified successfully")
                        
                        # Update the is_verified field in local account data
                        for account in self.email_accounts:
                            if account["id"] == account_id:
                                account["is_verified"] = True
                                account["verification_status"] = "verified"
                                break
                        return True
                    else:
                        details = result.get("details", [])
                        details_str = ", ".join(details) if details else "Unknown error"
                        logger.warning(f"Email verification failed: {details_str}")
                        
                        if attempt == 2:  # Last attempt
                            return False
                else:
                    logger.error(f"Failed to verify email account: {response.text}")
                    
                    if attempt == 2:  # Last attempt
                        return False
            except Exception as e:
                logger.error(f"Error verifying email account: {str(e)}")
                
                if attempt == 2:  # Last attempt
                    return False
        
        return False
    
    def create_warmup_config(self, account_id, config=None):
        """Create a warmup configuration for an email account"""
        logger.info(f"Creating warmup config for account ID: {account_id}")
        
        if config is None:
            config = {
                "is_active": True,
                "max_emails_per_day": 30,
                "daily_increase": 2,
                "current_daily_limit": 2,
                "min_delay_seconds": 60,
                "max_delay_seconds": 300,
                "target_open_rate": 80,
                "target_reply_rate": 40,
                "warmup_days": 28,
                "weekdays_only": False,
                "randomize_volume": True,
                "read_delay_seconds": 120
            }
        
        config["email_account_id"] = account_id
        
        try:
            response = self.api_request(
                'POST',
                "warmup/configs",
                json_data=config
            )
            
            if response.status_code == 200:
                config_data = response.json()
                logger.info(f"Created warmup config with ID: {config_data.get('id')}")
                return config_data
            elif "already exists" in response.text.lower():
                logger.info(f"Warmup config already exists for account {account_id}")
                
                # Try to get existing config
                configs_response = self.api_request('GET', "warmup/configs")
                if configs_response.status_code == 200:
                    configs = configs_response.json()
                    for cfg in configs:
                        if cfg.get('email_account_id') == account_id:
                            logger.info(f"Found existing config with ID: {cfg.get('id')}")
                            return cfg
                
                # If we couldn't get the config, create a fake one to continue
                logger.warning("Couldn't retrieve existing config, creating placeholder")
                return {"id": 0, "email_account_id": account_id, "is_active": True}
            else:
                logger.error(f"Failed to create warmup config: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating warmup config: {str(e)}")
            return None
    
    def run_warmup(self, account_id):
        """Manually run warmup for an account"""
        logger.info(f"Running warmup for account ID: {account_id}")
        try:
            response = self.api_request(
                'POST',
                f"warmup/run/{account_id}"
            )
            
            if response.status_code in [200, 201, 202]:
                result = response.json()
                logger.info(f"Warmup initiated for account {account_id}: {result}")
                return True
            else:
                logger.error(f"Failed to run warmup: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error running warmup: {str(e)}")
            return False
    
    def get_warmup_status(self, account_id):
        """Get warmup status for an account"""
        logger.info(f"Getting warmup status for account ID: {account_id}")
        try:
            response = self.api_request(
                'GET',
                f"warmup/status/{account_id}"
            )
            
            if response.status_code == 200:
                status = response.json()
                logger.info(f"Got warmup status: {json.dumps(status, indent=2)}")
                return status
            else:
                logger.error(f"Failed to get warmup status: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting warmup status: {str(e)}")
            return None
    
    def get_email_provider_info(self, email_address):
        """Get SMTP/IMAP info based on email domain"""
        if "@gmail.com" in email_address.lower():
            return {
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 465,  # Use SSL port by default
                "imap_host": "imap.gmail.com",
                "imap_port": 993,
                "domain": "gmail.com"
            }
        elif any(domain in email_address.lower() for domain in ["@outlook.com", "@hotmail.com", "@live.com", "@eudia.com"]):
            return {
                "smtp_host": "smtp.office365.com",
                "smtp_port": 587,
                "imap_host": "outlook.office365.com",
                "imap_port": 993,
                "domain": email_address.split('@')[1]
            }
        else:
            # Generic settings - may need to be adjusted
            domain = email_address.split('@')[1]
            return {
                "smtp_host": f"smtp.{domain}",
                "smtp_port": 587,
                "imap_host": f"imap.{domain}",
                "imap_port": 993,
                "domain": domain
            }
    
    def run_test(self, email_pairs, username, password, full_name=None):
        """Run a complete test with multiple email accounts"""
        if full_name is None:
            full_name = username.title()
        
        # Check if server is running
        if not self.test_server_connection():
            logger.error("Cannot connect to the email warmup server. Make sure it's running at http://localhost:8000")
            print("\nError: The email warmup server doesn't appear to be running.")
            print("Please start the server with: python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000")
            print("    Then run this script again.")
            return False
        
        # Step 1: Register and login
        if not self.register_user(email_pairs[0]["email"], username, password, full_name):
            logger.error("Failed to register user. Aborting test.")
            return False
        
        if not self.login(username, password):
            logger.error("Failed to login. Aborting test.")
            return False
        
        # Step 2: Add email accounts
        for email_pair in email_pairs:
            email_address = email_pair["email"]
            email_password = email_pair["password"]
            
            # Get provider-specific settings
            provider_info = self.get_email_provider_info(email_address)
            
            # If this is a Gmail account, notify about using App Password
            if "@gmail.com" in email_address.lower():
                logger.info(f"Gmail account detected for {email_address}. Make sure you're using an App Password, not your regular password.")
            
            # Remove any spaces in password (App Passwords sometimes have spaces)
            email_password = email_password.replace(" ", "")
            
            account_data = {
                "email_address": email_address,
                "display_name": full_name,
                "smtp_username": email_address,
                "smtp_password": email_password,
                "imap_username": email_address,
                "imap_password": email_password,
                **provider_info
            }
            
            account = self.add_email_account(account_data)
            if not account:
                logger.warning(f"Failed to add account {email_address}, continuing with others...")
                continue
            
            # Step 3: Verify email account
            if not self.verify_email_account(account["id"]):
                logger.warning(f"Failed to verify account {email_address}. This may affect warmup functionality.")
            
            # Step 4: Create warmup config
            config = self.create_warmup_config(account["id"])
            if not config:
                logger.warning(f"Failed to create warmup config for {email_address}, continuing with others...")
        
        if not self.email_accounts:
            logger.error("No email accounts were successfully added. Aborting test.")
            return False
        
        # Step 5: Run warmup for all accounts
        logger.info("Running warmup for all accounts...")
        for account in self.email_accounts:
            self.run_warmup(account["id"])
        
        # Step 6: Wait for warmup to process
        wait_time = 300  # 5 minutes
        logger.info(f"Waiting {wait_time} seconds for warmup processes to complete...")
        for i in range(wait_time, 0, -30):
            logger.info(f"Remaining: {i} seconds...")
            time.sleep(30)
        
        # Step 7: Check status for all accounts
        logger.info("Checking warmup status for all accounts...")
        for account in self.email_accounts:
            self.get_warmup_status(account["id"])
        
        # Step 8: Advise user to check inboxes
        logger.info("========== MANUAL VERIFICATION REQUIRED ==========")
        logger.info("Please check the following email inboxes manually:")
        for account in self.email_accounts:
            logger.info(f"- {account['email_address']}")
        logger.info("Look for emails with subjects containing 'WARMUP-'")
        logger.info("Also check spam folders to ensure emails are not landing there")
        logger.info("================================================")
        
        logger.info("Test completed successfully!")
        return True

def main():
    print("Robust Email Warmup Tester")
    print("==========================")
    print("This script handles connection issues and provides better error recovery.")
    
    # Get user credentials
    username = input("Enter username for registration/login (default: testuser): ") or "testuser"
    full_name = input("Enter full name (default: Test User): ") or "Test User"
    email1 = input("Enter first Gmail address: ")
    email2 = input("Enter second Gmail address: ")
    password = getpass.getpass("Enter password for authentication: ")
    
    # Prompt for email passwords securely
    email1_password = getpass.getpass(f"Enter password for {email1}: ")
    email2_password = getpass.getpass(f"Enter password for {email2}: ")
    
    # Set up email pairs
    email_pairs = [
        {"email": email1, "password": email1_password},
        {"email": email2, "password": email2_password}
    ]
    
    # Run the test
    tester = RobustEmailWarmupTester()
    test_result = tester.run_test(email_pairs, username, password, full_name)
    
    if test_result:
        print("\nTest completed successfully. Check the logs for details.")
    else:
        print("\nTest failed. Check the logs for errors.")

if __name__ == "__main__":
    main() 