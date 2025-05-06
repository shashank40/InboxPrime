#!/usr/bin/env python3
import asyncio
import logging
import time
import os
import json
import uuid
import getpass
import requests
import re
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urljoin

# Set up logging
log_format = '%(asctime)s - %(levelname)s - %(message)s'
log_filename = f"complete_system_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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

class CompleteSystemTester:
    """Tests all aspects of the email warmup system"""
    
    def __init__(self, base_url=API_BASE_URL):
        self.base_url = base_url
        self.auth_token = None
        self.user_id = None
        self.email_accounts = []
        self.configs = []
        self.db_path = "./email_warmup.db"  # Default SQLite database path
    
    def print_section(self, title):
        """Print a section title with formatting"""
        separator = "=" * (len(title) + 4)
        print(f"\n{separator}")
        print(f"  {title}")
        print(f"{separator}\n")
        logger.info(f"=== {title} ===")
    
    def _make_url(self, endpoint):
        """Construct full URL for endpoint"""
        return urljoin(self.base_url, endpoint)
    
    def _make_headers(self, with_auth=True):
        """Create headers for API requests"""
        headers = {"Content-Type": "application/json"}
        if with_auth and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
    
    def api_request(self, method, endpoint, json_data=None, data=None, with_auth=True):
        """Make API request with proper error handling"""
        url = self._make_url(endpoint)
        headers = self._make_headers(with_auth)
        content_type = headers.get("Content-Type")
        
        if content_type == "application/x-www-form-urlencoded" and data is None:
            # Convert JSON data to form data if needed
            data = json_data
            json_data = None
        
        # Special case for token endpoint
        if endpoint == "auth/token":
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            logger.info(f"Making {method} request to {endpoint}")
            
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
            
            if response.status_code >= 400:
                logger.error(f"API Error ({response.status_code}): {response.text}")
            else:
                logger.info(f"API Success ({response.status_code})")
            
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"API Request failed: {str(e)}")
            return None
    
    def test_server_connection(self):
        """Test if the server is running"""
        self.print_section("Testing Server Connection")
        
        try:
            # Try health endpoint first
            response = requests.get(self._make_url("health"))
            if response.status_code == 200:
                print("✅ Server is running (health endpoint available)")
                return True
            
            # If health endpoint not available, try docs endpoint
            response = requests.get("http://localhost:8000/docs")
            if response.status_code == 200:
                print("✅ Server is running (docs endpoint available)")
                return True
            
            # Try root endpoint as last resort
            response = requests.get("http://localhost:8000/")
            if response.status_code != 404:
                print("✅ Server is running (root endpoint available)")
                return True
            
            print("❌ Server not responding on any endpoint")
            return False
            
        except requests.exceptions.ConnectionError:
            print("❌ Connection error - server is not running")
            print("Please start the server with: python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000")
            return False
    
    def register_user(self, email, username, password, full_name):
        """Register a test user"""
        self.print_section("Registering Test User")
        
        try:
            response = self.api_request(
                'POST', 
                "auth/register",
                json_data={
                    "email": email,
                    "username": username,
                    "password": password,
                    "full_name": full_name
                },
                with_auth=False
            )
            
            if response and response.status_code == 200:
                print(f"✅ User {username} registered successfully")
                return True
            elif response and response.status_code == 409:
                print(f"ℹ️ User {username} already exists, will proceed with login")
                return True
            else:
                print(f"❌ Failed to register user: {response.text if response else 'No response'}")
                return False
        except Exception as e:
            print(f"❌ Error during registration: {str(e)}")
            return False
    
    def login_user(self, username, password):
        """Log in and get authentication token"""
        self.print_section("Logging In")
        
        try:
            response = self.api_request(
                'POST',
                "auth/token",
                data={
                    "username": username,
                    "password": password
                },
                with_auth=False
            )
            
            if response and response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                print(f"✅ Logged in successfully as {username}")
                
                # Get user details
                me_response = self.api_request('GET', "users/me")
                if me_response and me_response.status_code == 200:
                    user_data = me_response.json()
                    self.user_id = user_data.get("id")
                    print(f"✅ Got user details - ID: {self.user_id}")
                
                return True
            else:
                print(f"❌ Login failed: {response.text if response else 'No response'}")
                return False
        except Exception as e:
            print(f"❌ Error during login: {str(e)}")
            return False
    
    def add_email_account(self, email_data):
        """Add an email account to the system"""
        self.print_section(f"Adding Email Account: {email_data['email_address']}")
        
        try:
            # Ensure domain is present
            if 'domain' not in email_data and 'email_address' in email_data:
                email_data['domain'] = email_data['email_address'].split('@')[1]
            
            response = self.api_request(
                'POST',
                "emails",
                json_data=email_data
            )
            
            if response and response.status_code == 200:
                account = response.json()
                print(f"✅ Added email account with ID: {account.get('id')}")
                self.email_accounts.append(account)
                return account
            elif response and response.status_code == 400 and "already registered" in response.text:
                print(f"ℹ️ Email {email_data['email_address']} already registered, retrieving existing account")
                
                # Get existing accounts
                accounts_response = self.api_request('GET', "emails")
                if accounts_response and accounts_response.status_code == 200:
                    accounts = accounts_response.json()
                    for account in accounts:
                        if account['email_address'] == email_data['email_address']:
                            print(f"✅ Found existing account with ID: {account['id']}")
                            self.email_accounts.append(account)
                            return account
                
                print(f"❌ Could not retrieve existing account")
                return None
            else:
                print(f"❌ Failed to add email account: {response.text if response else 'No response'}")
                return None
        except Exception as e:
            print(f"❌ Error adding email account: {str(e)}")
            return None
    
    def verify_account(self, account_id):
        """Verify email account credentials"""
        self.print_section(f"Verifying Email Account: {account_id}")
        
        try:
            response = self.api_request(
                'POST',
                f"emails/{account_id}/verify"
            )
            
            if response and response.status_code == 200:
                result = response.json()
                success = result.get("success", False) or result.get("status") == "success"
                
                if success:
                    print(f"✅ Account verification successful")
                    
                    # Update account status in our local data
                    for account in self.email_accounts:
                        if account["id"] == account_id:
                            account["is_verified"] = True
                            break
                    
                    return True
                else:
                    details = result.get("details", [])
                    details_str = ", ".join(details) if details else "Unknown error"
                    print(f"❌ Verification failed: {details_str}")
                    return False
            else:
                print(f"❌ Verification request failed: {response.text if response else 'No response'}")
                return False
        except Exception as e:
            print(f"❌ Error during verification: {str(e)}")
            return False
    
    def create_warmup_config(self, account_id, config_data=None):
        """Create warmup configuration for an account"""
        self.print_section(f"Creating Warmup Config for Account: {account_id}")
        
        if config_data is None:
            config_data = {
                "email_account_id": account_id,
                "is_active": True,
                "max_emails_per_day": 30,
                "daily_increase": 2,
                "current_daily_limit": 3,
                "min_delay_seconds": 60,
                "max_delay_seconds": 300,
                "target_open_rate": 80,
                "target_reply_rate": 50,  # Higher than default to test more replies
                "warmup_days": 28,
                "weekdays_only": False,
                "randomize_volume": True,
                "read_delay_seconds": 120
            }
        
        # Make sure account_id is set
        config_data["email_account_id"] = account_id
        
        try:
            response = self.api_request(
                'POST',
                "warmup/configs",
                json_data=config_data
            )
            
            if response and response.status_code == 200:
                config = response.json()
                print(f"✅ Created warmup config with ID: {config.get('id')}")
                self.configs.append(config)
                return config
            elif response and "already exists" in response.text.lower():
                print(f"ℹ️ Warmup config already exists for account {account_id}, updating it")
                
                # Get existing configs
                configs_response = self.api_request('GET', "warmup/configs")
                if configs_response and configs_response.status_code == 200:
                    configs = configs_response.json()
                    for config in configs:
                        if config.get('email_account_id') == account_id:
                            config_id = config.get('id')
                            print(f"✅ Found existing config with ID: {config_id}")
                            
                            # Update the existing config
                            update_response = self.api_request(
                                'PUT',
                                f"warmup/configs/{config_id}",
                                json_data=config_data
                            )
                            
                            if update_response and update_response.status_code == 200:
                                updated_config = update_response.json()
                                print(f"✅ Updated existing warmup config")
                                self.configs.append(updated_config)
                                return updated_config
                            
                            # Even if update fails, return the existing config
                            self.configs.append(config)
                            return config
                
                print(f"❌ Could not retrieve existing config")
                return None
            else:
                print(f"❌ Failed to create warmup config: {response.text if response else 'No response'}")
                return None
        except Exception as e:
            print(f"❌ Error creating warmup config: {str(e)}")
            return None
    
    def update_warmup_config(self, config_id, update_data):
        """Update an existing warmup configuration"""
        self.print_section(f"Updating Warmup Config: {config_id}")
        
        try:
            response = self.api_request(
                'PUT',
                f"warmup/configs/{config_id}",
                json_data=update_data
            )
            
            if response and response.status_code == 200:
                updated_config = response.json()
                print(f"✅ Updated warmup config successfully")
                
                # Update in our local data
                for i, config in enumerate(self.configs):
                    if config.get('id') == config_id:
                        self.configs[i] = updated_config
                        break
                
                return updated_config
            else:
                print(f"❌ Failed to update config: {response.text if response else 'No response'}")
                return None
        except Exception as e:
            print(f"❌ Error updating config: {str(e)}")
            return None
    
    def run_warmup(self, account_id):
        """Manually run warmup process for an account"""
        self.print_section(f"Running Warmup for Account: {account_id}")
        
        try:
            response = self.api_request(
                'POST',
                f"warmup/run/{account_id}"
            )
            
            if response and response.status_code in [200, 201, 202]:
                result = response.json()
                print(f"✅ Warmup started successfully")
                
                # Print some details from the response
                emails_sent = result.get("emails_sent", 0)
                errors = result.get("errors", [])
                
                print(f"  Emails sent: {emails_sent}")
                if emails_sent == 0:
                    print("  ⚠️ No emails were sent during this warmup run. This could be because:")
                    print("     - The daily email limit has already been reached")
                    print("     - There are not enough recipient accounts in the system")
                    print("     - The warmup process is still initializing")
                
                if errors:
                    print(f"  Errors encountered: {len(errors)}")
                    for error in errors[:3]:  # Show first 3 errors
                        print(f"    - {error}")
                    if len(errors) > 3:
                        print(f"    - (and {len(errors) - 3} more)")
                
                return result
            else:
                print(f"❌ Failed to run warmup: {response.text if response else 'No response'}")
                return None
        except Exception as e:
            print(f"❌ Error running warmup: {str(e)}")
            return None
    
    def get_warmup_status(self, account_id):
        """Get current warmup status for an account"""
        self.print_section(f"Getting Warmup Status for Account: {account_id}")
        
        try:
            response = self.api_request(
                'GET',
                f"warmup/status/{account_id}"
            )
            
            if response and response.status_code == 200:
                status = response.json()
                print(f"✅ Retrieved warmup status")
                
                # Print key metrics
                print(f"  Current daily limit: {status.get('current_daily_limit', 'N/A')}")
                print(f"  Days in warmup: {status.get('days_in_warmup', 'N/A')}")
                print(f"  Warmup progress: {status.get('warmup_progress', 'N/A')}%")
                print(f"  Deliverability score: {status.get('deliverability_score', 'N/A')}")
                print(f"  Spam rate: {status.get('spam_rate', 'N/A')}%")
                print(f"  Open rate: {status.get('open_rate', 'N/A')}%")
                print(f"  Reply rate: {status.get('reply_rate', 'N/A')}%")
                print(f"  Total emails sent: {status.get('total_emails_sent', 'N/A')}")
                print(f"  Total emails received: {status.get('total_emails_received', 'N/A')}")
                
                return status
            else:
                print(f"❌ Failed to get warmup status: {response.text if response else 'No response'}")
                return None
        except Exception as e:
            print(f"❌ Error getting warmup status: {str(e)}")
            return None
    
    def get_dashboard_stats(self):
        """Get overall dashboard statistics"""
        self.print_section("Getting Dashboard Statistics")
        
        try:
            response = self.api_request(
                'GET',
                "dashboard/stats"
            )
            
            if response and response.status_code == 200:
                stats = response.json()
                print(f"✅ Retrieved dashboard statistics")
                
                # Print key metrics
                print(f"  Total accounts: {stats.get('total_accounts', 'N/A')}")
                print(f"  Active accounts: {stats.get('active_accounts', 'N/A')}")
                print(f"  Total emails sent: {stats.get('total_emails_sent', 'N/A')}")
                print(f"  Total emails received: {stats.get('total_emails_received', 'N/A')}")
                print(f"  Average deliverability score: {stats.get('avg_deliverability_score', 'N/A')}")
                print(f"  Average spam rate: {stats.get('avg_spam_rate', 'N/A')}%")
                
                return stats
            else:
                print(f"❌ Failed to get dashboard stats: {response.text if response else 'No response'}")
                return None
        except Exception as e:
            print(f"❌ Error getting dashboard stats: {str(e)}")
            return None
    
    def get_account_history(self, account_id):
        """Get historical metrics for an account"""
        self.print_section(f"Getting History for Account: {account_id}")
        
        try:
            response = self.api_request(
                'GET',
                f"dashboard/history/{account_id}"
            )
            
            if response and response.status_code == 200:
                history = response.json()
                print(f"✅ Retrieved account history")
                
                # Print summary of historical data
                print(f"  Days of data: {len(history)}")
                
                if history:
                    # Get the most recent day's data
                    recent = history[-1] if history else {}
                    print(f"  Most recent data ({recent.get('date', 'Unknown')}):")
                    print(f"    Emails sent: {recent.get('emails_sent', 'N/A')}")
                    print(f"    Emails received: {recent.get('emails_received', 'N/A')}")
                    print(f"    Emails in spam: {recent.get('emails_in_spam', 'N/A')}")
                    print(f"    Deliverability score: {recent.get('deliverability_score', 'N/A')}")
                
                return history
            else:
                print(f"❌ Failed to get account history: {response.text if response else 'No response'}")
                return None
        except Exception as e:
            print(f"❌ Error getting account history: {str(e)}")
            return None
    
    def check_database_records(self):
        """Directly check database records to verify data storage"""
        self.print_section("Checking Database Records")
        
        if not os.path.exists(self.db_path):
            print(f"❌ Database file not found at: {self.db_path}")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check email accounts
            cursor.execute("SELECT COUNT(*) FROM email_accounts")
            account_count = cursor.fetchone()[0]
            print(f"✅ Found {account_count} email accounts in database")
            
            # Check warmup configs
            cursor.execute("SELECT COUNT(*) FROM warmup_configs")
            config_count = cursor.fetchone()[0]
            print(f"✅ Found {config_count} warmup configs in database")
            
            # Check warmup emails
            cursor.execute("SELECT COUNT(*) FROM warmup_emails")
            email_count = cursor.fetchone()[0]
            print(f"✅ Found {email_count} warmup emails in database")
            
            results = {
                'accounts': account_count,
                'configs': config_count,
                'total_emails': email_count
            }
            
            # Check emails in spam
            cursor.execute("SELECT COUNT(*) FROM warmup_emails WHERE in_spam = 1")
            spam_count = cursor.fetchone()[0]
            print(f"✅ Found {spam_count} emails marked as spam in database")
            results['spam_emails'] = spam_count
            
            # Check warmup stats
            cursor.execute("SELECT COUNT(*) FROM warmup_stats")
            stat_count = cursor.fetchone()[0]
            print(f"✅ Found {stat_count} warmup stat records in database")
            results['stats'] = stat_count
            
            # Check recent emails sent
            cursor.execute("""
                SELECT COUNT(*) FROM warmup_emails 
                WHERE sent_at >= datetime('now', '-1 hour')
            """)
            recent_emails = cursor.fetchone()[0]
            print(f"✅ Found {recent_emails} emails sent in the last hour")
            results['recent_emails'] = recent_emails
            
            # Show some sample data from the most recent warmup emails
            cursor.execute("""
                SELECT id, sender_id, recipient_id, subject, status, in_spam, 
                       sent_at, delivered_at, opened_at, replied_at 
                FROM warmup_emails 
                ORDER BY id DESC LIMIT 5
            """)
            recent_emails = cursor.fetchall()
            
            if recent_emails:
                print("\nMost recent warmup emails:")
                for email in recent_emails:
                    print(f"  ID: {email[0]}, From: {email[1]}, To: {email[2]}, Status: {email[4]}, In Spam: {email[5]}")
                    print(f"  Subject: {email[3]}")
                    print(f"  Sent: {email[6]}, Delivered: {email[7]}, Opened: {email[8]}, Replied: {email[9]}")
                    print()
            else:
                print("\n⚠️ No warmup emails found in database")
            
            # Check if there are any recipient accounts available
            cursor.execute("""
                SELECT COUNT(*) FROM email_accounts 
                WHERE is_active = 1 AND is_verified = 1
            """)
            active_accounts = cursor.fetchone()[0]
            print(f"✅ Found {active_accounts} active and verified accounts in the system")
            results['active_accounts'] = active_accounts
            
            if active_accounts < 2:
                print("⚠️ You need at least 2 active accounts for warmup to work properly")
                print("   One account to send emails and another to receive them")
            
            conn.close()
            return results
        except Exception as e:
            print(f"❌ Error checking database: {str(e)}")
            return False
    
    def run_full_test(self, email_pairs, username, password, full_name=None):
        """Run a complete test of all system functionality"""
        if full_name is None:
            full_name = username.title()
        
        print("\n" + "=" * 80)
        print("     COMPLETE EMAIL WARMUP SYSTEM TEST")
        print("=" * 80)
        
        # Step 1: Check if server is running
        if not self.test_server_connection():
            print("\n❌ Cannot proceed with tests - server is not running")
            return False
        
        # Step 2: Register and login
        if not self.register_user(email_pairs[0]["email"], username, password, full_name):
            print("\n❌ User registration failed, cannot proceed")
            return False
        
        if not self.login_user(username, password):
            print("\n❌ Login failed, cannot proceed")
            return False
        
        # Step 3: Add email accounts
        for email_pair in email_pairs:
            email_address = email_pair["email"]
            email_password = email_pair["password"]
            
            # Determine provider settings based on email domain
            if "@gmail.com" in email_address.lower():
                provider_settings = {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 465,
                    "imap_host": "imap.gmail.com",
                    "imap_port": 993,
                    "domain": "gmail.com"
                }
            else:
                # Generic settings for other providers
                domain = email_address.split('@')[1]
                provider_settings = {
                    "smtp_host": f"smtp.{domain}",
                    "smtp_port": 587,
                    "imap_host": f"imap.{domain}",
                    "imap_port": 993,
                    "domain": domain
                }
            
            account_data = {
                "email_address": email_address,
                "display_name": full_name,
                "smtp_username": email_address,
                "smtp_password": email_password,
                "imap_username": email_address,
                "imap_password": email_password,
                **provider_settings
            }
            
            account = self.add_email_account(account_data)
            if not account:
                print(f"\n⚠️ Failed to add account {email_address}, will continue with other accounts")
                continue
            
            # Step 4: Verify the email account
            if not self.verify_account(account["id"]):
                print(f"\n⚠️ Failed to verify account {email_address}, will continue")
            
            # Step 5: Create warmup config with higher daily limit for testing
            config_data = {
                "email_account_id": account["id"],
                "is_active": True,
                "max_emails_per_day": 30,
                "daily_increase": 2,
                "current_daily_limit": 5,  # Increased from 3 to ensure emails are sent
                "min_delay_seconds": 30,   # Decreased to speed up testing
                "max_delay_seconds": 60,   # Decreased to speed up testing
                "target_open_rate": 80,
                "target_reply_rate": 50,
                "warmup_days": 28,
                "weekdays_only": False,
                "randomize_volume": True,
                "read_delay_seconds": 60
            }
            
            config = self.create_warmup_config(account["id"], config_data)
            if not config:
                print(f"\n⚠️ Failed to create warmup config for {email_address}")
        
        if not self.email_accounts:
            print("\n❌ No email accounts were successfully added")
            return False
        
        # Step 6: Update a warmup config to test the update functionality
        if self.configs:
            first_config = self.configs[0]
            self.update_warmup_config(first_config.get('id'), {
                "daily_increase": 3,
                "target_reply_rate": 60
            })
        
        # Step 7: Run warmup for all accounts
        for account in self.email_accounts:
            self.run_warmup(account["id"])
        
        # Step 8: Wait for warmup process to run (increased to 2 minutes)
        self.print_section("Waiting for Warmup Process")
        print("Waiting 120 seconds for warmup processes to complete...")
        print("(This may take time as emails are sent with random delays)")
        for i in range(12):
            time.sleep(10)
            print(f"  {(i+1)*10} seconds elapsed...")
            
            # Check every 30 seconds if any emails have been sent
            if (i+1) % 3 == 0:
                print("\nChecking progress...")
                for account in self.email_accounts:
                    response = self.api_request(
                        'GET',
                        f"warmup/status/{account['id']}"
                    )
                    if response and response.status_code == 200:
                        status = response.json()
                        emails_sent = status.get('total_emails_sent', 0)
                        print(f"  Account {account['email_address']}: {emails_sent} total emails sent")
        
        # Step 9: Check warmup status for all accounts
        for account in self.email_accounts:
            self.get_warmup_status(account["id"])
        
        # Step 10: Get dashboard statistics
        self.get_dashboard_stats()
        
        # Step 11: Get historical data for first account
        if self.email_accounts:
            self.get_account_history(self.email_accounts[0]["id"])
        
        # Step 12: Check database records directly
        email_records = self.check_database_records()
        
        # Step 13: Suggest manual email check if no emails were detected
        if email_records and email_records.get('total_emails', 0) == 0:
            self.print_section("Manual Email Check Required")
            print("⚠️ No emails were detected in the database.")
            print("Please check your email accounts manually for the following reasons:")
            print("1. The system might be configured to send emails at specific times")
            print("2. There might not be enough recipient accounts in the system")
            print("3. Daily email limits might have already been reached")
            print("4. There might be SMTP connection issues")
            print("\nTo force send test emails directly, you can run:")
            print("python test_end_to_end.py")
        
        # Summary
        self.print_section("Test Summary")
        print("Complete system test finished. Check the detailed log for results.")
        print(f"Log file: {log_filename}")
        
        return True

def main():
    print("Email Warmup Complete System Test")
    print("=================================")
    print("This test will verify all functionality of the email warmup system.")
    print("You'll need at least 2 Gmail accounts with App Passwords set up.")
    print()
    
    # Get user input
    username = input("Enter username for account (default: testuser): ") or "testuser"
    password = getpass.getpass("Enter password for system login: ")
    
    email_pairs = []
    
    email1 = input("Enter first Gmail address: ")
    password1 = getpass.getpass(f"Enter App Password for {email1}: ")
    email_pairs.append({"email": email1, "password": password1.replace(" ", "")})
    
    email2 = input("Enter second Gmail address: ")
    password2 = getpass.getpass(f"Enter App Password for {email2}: ")
    email_pairs.append({"email": email2, "password": password2.replace(" ", "")})
    
    # Run the complete test
    tester = CompleteSystemTester()
    tester.run_full_test(email_pairs, username, password)

if __name__ == "__main__":
    main() 