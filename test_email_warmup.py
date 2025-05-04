#!/usr/bin/env python3
import os
import sys
import json
import argparse
import asyncio
import logging
import time
from datetime import datetime
import getpass
import requests
from urllib.parse import urljoin
import glob

# Configure logging
log_format = '%(asctime)s - %(levelname)s - %(message)s'
log_filename = f"email_warmup_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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
AUTH_TOKEN = None

class EmailWarmupTester:
    def __init__(self, base_url=API_BASE_URL):
        self.base_url = base_url
        self.auth_token = None
        self.user_id = None
        self.email_accounts = []
    
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
    
    def register_user(self, email, username, password, full_name):
        """Register a new user in the system"""
        logger.info(f"Registering user: {username}")
        try:
            response = requests.post(
                self._make_url("auth/register"),
                headers=self._make_headers(with_auth=False),
                json={
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
            response = requests.post(
                self._make_url("auth/token"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "username": username,
                    "password": password
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                logger.info("Login successful")
                
                # Get user information
                me_response = requests.get(
                    self._make_url("users/me"),
                    headers=self._make_headers()
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
        """Add an email account to the system"""
        logger.info(f"Adding email account: {email_data['email_address']}")
        try:
            response = requests.post(
                self._make_url("emails"),
                headers=self._make_headers(),
                json=email_data
            )
            
            if response.status_code == 200:
                account = response.json()
                logger.info(f"Added email account with ID: {account['id']}")
                self.email_accounts.append(account)
                return account
            else:
                logger.error(f"Failed to add email account: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error adding email account: {str(e)}")
            return None
    
    def verify_email_account(self, account_id):
        """Verify an email account's credentials"""
        logger.info(f"Verifying email account with ID: {account_id}")
        try:
            response = requests.post(
                self._make_url(f"emails/{account_id}/verify"),
                headers=self._make_headers()
            )
            
            if response.status_code == 200:
                result = response.json()
                success = result.get("success", False)
                if success:
                    logger.info(f"Email account {account_id} verified successfully")
                else:
                    logger.warning(f"Email verification failed: {result.get('message', 'Unknown error')}")
                return success
            else:
                logger.error(f"Failed to verify email account: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error verifying email account: {str(e)}")
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
            response = requests.post(
                self._make_url("warmup/configs"),
                headers=self._make_headers(),
                json=config
            )
            
            if response.status_code == 200:
                config_data = response.json()
                logger.info(f"Created warmup config with ID: {config_data.get('id')}")
                return config_data
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
            response = requests.post(
                self._make_url(f"warmup/run/{account_id}"),
                headers=self._make_headers()
            )
            
            if response.status_code == 202:
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
            response = requests.get(
                self._make_url(f"warmup/status/{account_id}"),
                headers=self._make_headers()
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
    
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        logger.info("Getting dashboard statistics")
        try:
            response = requests.get(
                self._make_url("dashboard/stats"),
                headers=self._make_headers()
            )
            
            if response.status_code == 200:
                stats = response.json()
                logger.info(f"Got dashboard stats: {json.dumps(stats, indent=2)}")
                return stats
            else:
                logger.error(f"Failed to get dashboard stats: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {str(e)}")
            return None

    def check_account_inboxes(self):
        """Advise user to check inboxes manually"""
        if not self.email_accounts:
            logger.warning("No email accounts to check")
            return

        logger.info("========== MANUAL VERIFICATION REQUIRED ==========")
        logger.info("Please check the following email inboxes manually:")
        for account in self.email_accounts:
            logger.info(f"- {account['email_address']}")
        logger.info("Look for emails with subjects containing 'WARMUP-'")
        logger.info("Also check spam folders to ensure emails are not landing there")
        logger.info("================================================")

    def get_email_provider_info(self, email_address):
        """Get SMTP/IMAP info based on email domain"""
        if "@gmail.com" in email_address.lower():
            return {
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 465,
                "imap_host": "imap.gmail.com",
                "imap_port": 993,
                "domain": "gmail.com"
            }
        elif "@outlook.com" in email_address.lower() or "@hotmail.com" in email_address.lower() or "@live.com" in email_address.lower() or "@eudia.com" in email_address.lower():
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
        
        # Step 8: Get dashboard stats
        self.get_dashboard_stats()
        
        # Step 9: Advise user to check inboxes
        self.check_account_inboxes()
        
        logger.info("Test completed successfully!")
        return True


def delete_log_files():
    """Delete all email warmup test log files"""
    log_files = glob.glob("email_warmup_test_*.log")
    count = 0
    for log_file in log_files:
        try:
            os.remove(log_file)
            count += 1
        except Exception as e:
            logger.error(f"Failed to delete log file {log_file}: {str(e)}")
    
    if count > 0:
        print(f"Successfully deleted {count} log file(s).")
    else:
        print("No log files found to delete.")
    return count

def main():
    parser = argparse.ArgumentParser(description='Test Email Warmup System')
    parser.add_argument('--url', default='http://localhost:8000/api/', help='Base URL for the API')
    parser.add_argument('--username', default='testuser', help='Username for registration/login')
    parser.add_argument('--password', help='Password for registration/login')
    parser.add_argument('--name', help='Full name for registration')
    parser.add_argument('--delete-logs', action='store_true', help='Delete log files after test completion')
    
    # For simplicity, just add the two email addresses as arguments
    parser.add_argument('--email1', default='shashank.tiwari@eudia.com', help='First email address')
    parser.add_argument('--email2', default='tiwari.shashank408@gmail.com', help='Second email address')
    
    args = parser.parse_args()
    
    # Check if we should just delete logs and exit
    if args.delete_logs and len(sys.argv) == 2:
        delete_log_files()
        return
    
    # If password is not provided, prompt for it securely
    password = args.password
    if not password:
        password = getpass.getpass("Enter password for authentication: ")
    
    # Prompt for email passwords securely
    email1_password = getpass.getpass(f"Enter password for {args.email1}: ")
    email2_password = getpass.getpass(f"Enter password for {args.email2}: ")
    
    # Set up email pairs
    email_pairs = [
        {"email": args.email1, "password": email1_password},
        {"email": args.email2, "password": email2_password}
    ]
    
    # Run the test
    tester = EmailWarmupTester(args.url)
    test_result = tester.run_test(email_pairs, args.username, password, args.name)
    
    # Delete logs if requested and test completed
    if args.delete_logs and test_result:
        print("\nTest completed. Deleting log files...")
        delete_log_files()


if __name__ == "__main__":
    main() 