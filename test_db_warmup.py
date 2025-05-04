import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
import random
import string
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import database models and services
from app.db.database import SessionLocal, create_tables
from app.models.models import User, EmailAccount, WarmupConfig, WarmupEmail, WarmupStat
from app.services.warmup_service import WarmupService
from app.services.email_service import EmailService

# Mock email credentials
MOCK_ACCOUNTS = [
    {
        "email_address": f"test{random.randint(1000, 9999)}@example.com",
        "display_name": "Test Account 1",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "test1@example.com",
        "smtp_password": "password123",
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "imap_username": "test1@example.com",
        "imap_password": "password123",
        "domain": "example.com",
        "is_verified": True,  # Mock as verified
        "verification_status": "verified"
    },
    {
        "email_address": f"test{random.randint(1000, 9999)}@example.com",
        "display_name": "Test Account 2",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "test2@example.com",
        "smtp_password": "password123",
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "imap_username": "test2@example.com",
        "imap_password": "password123",
        "domain": "example.com",
        "is_verified": True,  # Mock as verified
        "verification_status": "verified"
    }
]

def create_test_user():
    """Create a test user in the database"""
    db = SessionLocal()
    try:
        # Check if user already exists
        user = db.query(User).filter(User.email == "test@example.com").first()
        if user:
            logger.info(f"Test user already exists (id: {user.id})")
            return user.id
        
        # Create new user
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_testpassword",  # In a real app, this would be properly hashed
            full_name="Test User",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created test user (id: {user.id})")
        return user.id
    finally:
        db.close()

def create_test_email_accounts(user_id):
    """Create test email accounts in the database"""
    db = SessionLocal()
    try:
        account_ids = []
        for account_data in MOCK_ACCOUNTS:
            # Check if email already exists
            existing = db.query(EmailAccount).filter(
                EmailAccount.email_address == account_data["email_address"]
            ).first()
            
            if existing:
                logger.info(f"Email account {account_data['email_address']} already exists")
                account_ids.append(existing.id)
                continue
            
            # Create new account
            account = EmailAccount(
                user_id=user_id,
                **account_data
            )
            db.add(account)
            db.commit()
            db.refresh(account)
            account_ids.append(account.id)
            logger.info(f"Created email account (id: {account.id}, email: {account.email_address})")
        
        return account_ids
    finally:
        db.close()

def create_test_warmup_configs(account_ids):
    """Create warmup configurations for test accounts"""
    db = SessionLocal()
    try:
        config_ids = []
        for account_id in account_ids:
            # Check if config already exists
            existing = db.query(WarmupConfig).filter(
                WarmupConfig.email_account_id == account_id
            ).first()
            
            if existing:
                logger.info(f"Warmup config for account {account_id} already exists")
                config_ids.append(existing.id)
                continue
            
            # Get the user_id for this account
            account = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
            if not account:
                logger.error(f"Account with id {account_id} not found")
                continue
                
            # Create new config
            config = WarmupConfig(
                user_id=account.user_id,
                email_account_id=account_id,
                is_active=True,
                max_emails_per_day=30,
                daily_increase=2,
                current_daily_limit=3,  # Start with 3 emails per day
                min_delay_seconds=5,    # Short delay for testing
                max_delay_seconds=10,   # Short delay for testing 
                target_open_rate=80.0,
                target_reply_rate=40.0,
                warmup_days=14,
                weekdays_only=False,
                randomize_volume=True,
                read_delay_seconds=5    # Short delay for testing
            )
            db.add(config)
            db.commit()
            db.refresh(config)
            config_ids.append(config.id)
            logger.info(f"Created warmup config for account {account_id}")
        
        return config_ids
    finally:
        db.close()

def create_mock_warmup_emails(account_ids, count=3):
    """Create mock warmup emails between accounts"""
    db = SessionLocal()
    try:
        email_ids = []
        
        # Get the domains for each account
        accounts = db.query(EmailAccount).filter(EmailAccount.id.in_(account_ids)).all()
        account_domains = {account.id: account.domain for account in accounts}
        
        for i in range(count):
            for sender_id in account_ids:
                for recipient_id in account_ids:
                    # Don't send to self
                    if sender_id == recipient_id:
                        continue
                    
                    # Create message ID
                    sender_domain = account_domains.get(sender_id, "example.com")
                    message_id = f"<mock-{random.randint(1000, 9999)}@{sender_domain}>"
                    
                    # Create warmup email
                    email = WarmupEmail(
                        message_id=message_id,
                        sender_id=sender_id,
                        recipient_id=recipient_id,
                        subject=f"WARMUP-TEST: Test email {i+1}",
                        body="<p>This is a test warmup email.</p>",
                        status="sent",
                        sent_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
                        delivered_at=datetime.utcnow() - timedelta(hours=random.randint(1, 23)),
                        in_spam=False
                    )
                    db.add(email)
                    
                    # Create an immediate reference for emails to be processed
                    db.flush()
                    email_ids.append(email.id)
                    
                    logger.info(f"Created mock warmup email from account {sender_id} to account {recipient_id}")
        
        # Commit all at once
        db.commit()
        
        return email_ids
    finally:
        db.close()

def process_mock_warmup_emails():
    """Mock processing of warmup emails (marking as opened/replied)"""
    db = SessionLocal()
    try:
        # Get all sent warmup emails
        sent_emails = db.query(WarmupEmail).filter(
            WarmupEmail.status == "sent",
            WarmupEmail.delivered_at.isnot(None)
        ).all()
        
        processed_count = 0
        for email in sent_emails:
            # Mark 80% as opened
            if random.random() < 0.8:
                email.status = "opened"
                email.opened_at = datetime.utcnow()
                processed_count += 1
                
                # Mark 50% of opened as replied
                if random.random() < 0.5:
                    email.status = "replied"
                    email.replied_at = datetime.utcnow()
                    
                    # Create a reply
                    reply = WarmupEmail(
                        message_id=f"<reply-{random.randint(1000, 9999)}@domain.com>",
                        sender_id=email.recipient_id,
                        recipient_id=email.sender_id,
                        subject=f"Re: {email.subject}",
                        body="<p>This is a test reply to your warmup email.</p>",
                        status="sent",
                        is_reply=True,
                        sent_at=datetime.utcnow(),
                        delivered_at=datetime.utcnow(),
                        in_spam=False
                    )
                    db.add(reply)
        
        db.commit()
        logger.info(f"Processed {processed_count} mock warmup emails")
    finally:
        db.close()

async def run_actual_warmup_cycle():
    """Run an actual warmup cycle using the WarmupService"""
    db = SessionLocal()
    try:
        # Patch the EmailService methods
        # We'll mock these to avoid actually sending emails
        original_send_email = EmailService.send_email
        original_check_inbox = EmailService.check_inbox
        
        async def mock_send_email(sender, recipient_email, subject, body_html, body_text):
            logger.info(f"MOCK: Sending email from {sender.email_address} to {recipient_email}")
            # Return success and a fake message ID
            message_id = f"<mock-{random.randint(1000, 9999)}@{sender.domain}>"
            return True, "Email sent successfully", message_id
        
        async def mock_check_inbox(email_account, look_for_warmup_emails=True, process_replies=True):
            logger.info(f"MOCK: Checking inbox for {email_account.email_address}")
            return {
                "total": random.randint(10, 50),
                "unread": random.randint(1, 10),
                "warmup": random.randint(1, 5),
                "warmup_replied": random.randint(0, 3),
                "in_spam": 0,
                "processed": [],
                "errors": []
            }
        
        # Apply the mocks
        EmailService.send_email = mock_send_email
        EmailService.check_inbox = mock_check_inbox
        
        try:
            # Run the warmup cycle
            logger.info("Running warmup cycle...")
            result = await WarmupService.run_warmup_cycle(db)
            
            logger.info(f"Warmup cycle completed:")
            logger.info(f"  Accounts processed: {result.get('accounts_processed', 0)}")
            logger.info(f"  Total emails sent: {result.get('total_emails_sent', 0)}")
            
            if result.get('errors', []):
                logger.warning(f"Errors encountered: {result.get('errors', [])}")
            
            return result
        finally:
            # Restore original methods
            EmailService.send_email = original_send_email
            EmailService.check_inbox = original_check_inbox
    finally:
        db.close()

async def test_warmup_service_individual_account(account_id):
    """Test warmup service for a specific account"""
    db = SessionLocal()
    try:
        # Patch the EmailService methods
        original_send_email = EmailService.send_email
        original_check_inbox = EmailService.check_inbox
        
        async def mock_send_email(sender, recipient_email, subject, body_html, body_text):
            logger.info(f"MOCK: Sending email from {sender.email_address} to {recipient_email}")
            return True, "Email sent successfully", f"<mock-{random.randint(1000, 9999)}@{sender.domain}>"
        
        async def mock_check_inbox(email_account, look_for_warmup_emails=True, process_replies=True):
            logger.info(f"MOCK: Checking inbox for {email_account.email_address}")
            return {
                "total": random.randint(10, 50),
                "unread": random.randint(1, 10),
                "warmup": random.randint(1, 5),
                "warmup_replied": random.randint(0, 3),
                "in_spam": 0,
                "processed": [],
                "errors": []
            }
        
        # Apply the mocks
        EmailService.send_email = mock_send_email
        EmailService.check_inbox = mock_check_inbox
        
        try:
            # First process incoming emails
            logger.info(f"Processing incoming emails for account {account_id}...")
            process_result = await WarmupService.process_incoming_warmup_emails(db, account_id)
            
            logger.info(f"Incoming email processing result:")
            logger.info(f"  Emails processed: {process_result.get('emails_processed', 0)}")
            logger.info(f"  Emails in spam: {process_result.get('emails_in_spam', 0)}")
            
            # Then send warmup emails
            logger.info(f"Sending warmup emails for account {account_id}...")
            send_result = await WarmupService.send_warmup_emails(db, account_id)
            
            logger.info(f"Warmup email sending result:")
            logger.info(f"  Success: {send_result.get('success', False)}")
            logger.info(f"  Emails sent: {send_result.get('emails_sent', 0)}")
            
            if send_result.get('errors', []):
                logger.warning(f"Errors encountered: {send_result.get('errors', [])}")
            
            return {
                "process_result": process_result,
                "send_result": send_result
            }
        finally:
            # Restore original methods
            EmailService.send_email = original_send_email
            EmailService.check_inbox = original_check_inbox
    finally:
        db.close()

async def get_warmup_status_for_account(account_id):
    """Get warmup status for an account"""
    db = SessionLocal()
    try:
        status = await WarmupService.get_warmup_status(db, account_id)
        
        if status.get("success", False):
            logger.info(f"Warmup status for account {account_id}:")
            logger.info(f"  Daily limit: {status.get('current_daily_limit')}")
            logger.info(f"  Days in warmup: {status.get('days_in_warmup')}")
            logger.info(f"  Warmup progress: {status.get('warmup_progress')}%")
            logger.info(f"  Deliverability score: {status.get('deliverability_score')}")
            logger.info(f"  Open rate: {status.get('open_rate')}%")
            logger.info(f"  Reply rate: {status.get('reply_rate')}%")
        else:
            logger.error(f"Failed to get warmup status: {status.get('error', 'Unknown error')}")
        
        return status
    finally:
        db.close()

async def main():
    """Main test function"""
    logger.info("Starting email warmup system test...")
    
    # Ensure tables exist
    create_tables()
    logger.info("Database tables created or verified")
    
    # Create test user
    user_id = create_test_user()
    
    # Create test email accounts (returns account IDs)
    account_ids = create_test_email_accounts(user_id)
    if not account_ids:
        logger.error("No test accounts created, aborting.")
        return
    
    # Create warmup configs for accounts
    config_ids = create_test_warmup_configs(account_ids)
    
    # Create some mock warmup emails
    email_ids = create_mock_warmup_emails(account_ids)
    
    # Process mock emails
    process_mock_warmup_emails()
    
    # Test warmup for the first account
    logger.info(f"Testing warmup for account {account_ids[0]}...")
    individual_result = await test_warmup_service_individual_account(account_ids[0])
    
    # Get status for the account
    await get_warmup_status_for_account(account_ids[0])
    
    # Run a complete warmup cycle
    logger.info("Running a complete warmup cycle...")
    cycle_result = await run_actual_warmup_cycle()
    
    # Get status for all accounts after cycle
    for account_id in account_ids:
        await get_warmup_status_for_account(account_id)
    
    logger.info("Email warmup system test completed successfully")
    
if __name__ == "__main__":
    asyncio.run(main()) 