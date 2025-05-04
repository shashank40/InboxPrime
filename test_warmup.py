import asyncio
import os
import sys
import json
import logging
from datetime import datetime, timedelta

import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API base URL
BASE_URL = "http://localhost:8000/api"
AUTH_TOKEN = None

# Test email accounts (replace with real credentials for actual testing)
TEST_ACCOUNTS = [
    {
        "email_address": "test1@example.com",
        "display_name": "Test Account 1",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "test1@example.com",
        "smtp_password": "your_password",
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "imap_username": "test1@example.com",
        "imap_password": "your_password"
    },
    {
        "email_address": "test2@example.com",
        "display_name": "Test Account 2",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "test2@example.com",
        "smtp_password": "your_password",
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "imap_username": "test2@example.com",
        "imap_password": "your_password"
    }
]

async def register_user():
    """Register a test user"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "testpassword",
                "full_name": "Test User"
            }
        )
        
        if response.status_code == 409:
            logger.info("User already exists, proceeding to login")
            return True
        elif response.status_code == 200:
            logger.info("User registered successfully")
            return True
        else:
            logger.error(f"Failed to register user: {response.text}")
            return False

async def login():
    """Login and get authentication token"""
    global AUTH_TOKEN
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/token",
            data={
                "username": "testuser",
                "password": "testpassword"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            data = response.json()
            AUTH_TOKEN = data.get("access_token")
            logger.info("Login successful, acquired authentication token")
            return True
        else:
            logger.error(f"Failed to login: {response.text}")
            return False

async def add_email_account(account_data):
    """Add an email account"""
    if not AUTH_TOKEN:
        logger.error("No authentication token available")
        return None
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/emails",
            json=account_data,
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        if response.status_code == 200:
            account = response.json()
            logger.info(f"Added email account: {account['email_address']}")
            return account
        else:
            logger.error(f"Failed to add email account: {response.text}")
            return None

async def verify_email_account(account_id):
    """Verify an email account's credentials"""
    if not AUTH_TOKEN:
        logger.error("No authentication token available")
        return False
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/emails/{account_id}/verify",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Email verification result: {result}")
            return result.get("success", False)
        else:
            logger.error(f"Failed to verify email account: {response.text}")
            return False

async def create_warmup_config(account_id):
    """Create a warmup configuration for an email account"""
    if not AUTH_TOKEN:
        logger.error("No authentication token available")
        return None
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/warmup/configs",
            json={
                "email_account_id": account_id,
                "is_active": True,
                "max_emails_per_day": 30,
                "daily_increase": 2,
                "current_daily_limit": 2,
                "min_delay_seconds": 30,
                "max_delay_seconds": 120,
                "target_open_rate": 80,
                "target_reply_rate": 40,
                "warmup_days": 14,
                "weekdays_only": False,
                "randomize_volume": True,
                "read_delay_seconds": 60
            },
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        if response.status_code == 200:
            config = response.json()
            logger.info(f"Created warmup config for account {account_id}")
            return config
        else:
            logger.error(f"Failed to create warmup config: {response.text}")
            return None

async def run_warmup_for_account(account_id):
    """Manually run warmup for an account"""
    if not AUTH_TOKEN:
        logger.error("No authentication token available")
        return False
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/warmup/run/{account_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        if response.status_code == 202:
            result = response.json()
            logger.info(f"Warmup initiated: {result}")
            return True
        else:
            logger.error(f"Failed to run warmup: {response.text}")
            return False

async def get_warmup_status(account_id):
    """Get warmup status for an account"""
    if not AUTH_TOKEN:
        logger.error("No authentication token available")
        return None
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/warmup/status/{account_id}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        if response.status_code == 200:
            status = response.json()
            logger.info(f"Warmup status: {json.dumps(status, indent=2)}")
            return status
        else:
            logger.error(f"Failed to get warmup status: {response.text}")
            return None

async def wait_and_check_status(account_id, wait_seconds=30):
    """Wait for a specified time and then check warmup status"""
    logger.info(f"Waiting {wait_seconds} seconds for warmup to process...")
    await asyncio.sleep(wait_seconds)
    return await get_warmup_status(account_id)

async def test_warmup_end_to_end():
    """Test the email warmup system end-to-end"""
    logger.info("Starting end-to-end test of email warmup system")
    
    # Step 1: Register user and login
    if not await register_user():
        return False
    
    if not await login():
        return False
    
    # Step 2: Add email accounts (first 2 from test accounts list)
    accounts = []
    for account_data in TEST_ACCOUNTS:
        account = await add_email_account(account_data)
        if account:
            accounts.append(account)
    
    if len(accounts) < 2:
        logger.error("Need at least 2 accounts for testing warmup")
        return False
    
    # Step 3: Verify email accounts
    # Note: This step will fail with fake credentials, so we'll skip actual verification
    # for test_account in accounts:
    #     verified = await verify_email_account(test_account["id"])
    #     if not verified:
    #         logger.warning(f"Could not verify account {test_account['email_address']}")
    
    # Instead, we'll mock the verification status by setting is_verified to True
    # This would normally be done via the database
    logger.info("In a real test, we would verify real email accounts here")
    logger.info("For this test, we'll assume accounts are verified")
    
    # Step 4: Create warmup configs
    configs = []
    for account in accounts:
        config = await create_warmup_config(account["id"])
        if config:
            configs.append(config)
    
    if not configs:
        logger.error("Failed to create warmup configurations")
        return False
    
    # Step 5: Run warmup for the first account
    if not await run_warmup_for_account(accounts[0]["id"]):
        logger.error("Failed to run warmup")
        return False
    
    # Step 6: Wait and check status
    status = await wait_and_check_status(accounts[0]["id"], 10)
    if not status:
        logger.error("Failed to get warmup status")
        return False
    
    # Step 7: Run warmup for the second account
    if not await run_warmup_for_account(accounts[1]["id"]):
        logger.error("Failed to run warmup for second account")
        return False
    
    # Step 8: Wait and check status again for both accounts
    for account in accounts:
        status = await wait_and_check_status(account["id"], 5)
        if not status:
            logger.warning(f"Could not get status for account {account['id']}")
    
    logger.info("End-to-end test completed successfully")
    return True

if __name__ == "__main__":
    logger.info("Starting email warmup system test")
    
    # Check if the server is running
    try:
        response = httpx.get(f"{BASE_URL}/auth/health-check", timeout=5)
        if response.status_code != 200:
            logger.error("API server is not responding correctly")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to connect to API server: {e}")
        logger.error("Make sure the server is running (uvicorn main:app --reload)")
        sys.exit(1)
    
    # Run the async test
    asyncio.run(test_warmup_end_to_end()) 