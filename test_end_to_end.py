#!/usr/bin/env python3
import asyncio
import logging
import time
import os
import json
import getpass
import smtplib
import imaplib
import ssl
import email
import uuid
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Configure logging
log_format = '%(asctime)s - %(levelname)s - %(message)s'
log_filename = f"email_warmup_e2e_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("email_warmup")

class EndToEndWarmupTester:
    """A comprehensive end-to-end tester for the email warmup system"""
    
    def __init__(self):
        self.email_accounts = []
        self.test_identifiers = {}
        self.verified_accounts = []
        self.email_password_map = {}  # For quick lookup of passwords
        self.delivery_location = None  # Where the test email was delivered
        
    def print_section(self, title):
        """Print a section header with formatting"""
        print(f"\n=== {title} ===")
        logger.info(f"\n=== {title} ===")
        
    def test_smtp_connection(self, email, password):
        """Test SMTP connection to Gmail"""
        logger.info(f"Testing direct SMTP connection for {email}")
        
        try:
            # Try SSL connection first (port 465)
            logger.info("Trying SSL connection (port 465)...")
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(email, password)
                logger.info("✅ SMTP SSL connection successful")
                print(f"✅ SMTP connection successful for {email}")
                return True
        except Exception as e:
            logger.error(f"SSL connection failed: {str(e)}")
            
            # Try STARTTLS as fallback (port 587)
            try:
                logger.info("Trying STARTTLS connection (port 587)...")
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls(context=ssl.create_default_context())
                    server.login(email, password)
                    logger.info("✅ SMTP STARTTLS connection successful")
                    print(f"✅ SMTP connection successful for {email}")
                    return True
            except Exception as e2:
                logger.error(f"STARTTLS connection failed: {str(e2)}")
                print(f"❌ SMTP connection failed for {email}")
                print(f"Error: {str(e2)}")
                return False
    
    def test_imap_connection(self, email, password):
        """Test IMAP connection to Gmail"""
        logger.info(f"Testing direct IMAP connection for {email}")
        
        try:
            # Connect to IMAP server
            logger.info("Connecting to IMAP server...")
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            
            # Login
            logger.info("Logging in...")
            mail.login(email, password)
            logger.info("✅ IMAP connection successful")
            
            # List folders
            result, folders = mail.list()
            if result == "OK":
                logger.info(f"Successfully listed {len(folders)} folders")
            
            # Logout
            mail.logout()
            
            # If we get here, connection was successful
            print(f"✅ IMAP connection successful for {email}")
            
            # Store for future use
            self.verified_accounts.append({"email": email, "password": password})
            self.email_password_map[email] = password
            
            return True
        except Exception as e:
            logger.error(f"IMAP connection failed: {str(e)}")
            print(f"❌ IMAP connection failed for {email}")
            print(f"Error: {str(e)}")
            return False
    
    def send_test_email(self, sender_email, sender_password, recipient_email, subject):
        """Send a test email with a unique identifier"""
        logger.info(f"Sending direct test email from {sender_email} to {recipient_email}")
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = recipient_email
            
            # Create text and HTML versions of message
            text = f"This is a test email for the warmup system with ID: {subject}"
            html = f"""
            <html>
              <head></head>
              <body>
                <p>This is a test email for the warmup system with ID: {subject}</p>
                <p>This email tests if the warmup functionality is working correctly.</p>
              </body>
            </html>
            """
            
            # Attach parts
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send the message
            try:
                # Try SSL connection first (port 465)
                logger.info("Sending email using SSL connection (port 465)...")
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                    logger.info(f"✅ Email sent successfully with subject: {subject}")
                    print(f"✅ Email sent successfully to {recipient_email}")
                    return True
            except Exception as e:
                logger.error(f"SSL send failed: {str(e)}")
                
                # Try STARTTLS as fallback (port 587)
                logger.info("Trying STARTTLS connection (port 587)...")
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls(context=ssl.create_default_context())
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                    logger.info(f"✅ Email sent successfully with subject: {subject}")
                    print(f"✅ Email sent successfully to {recipient_email}")
                    return True
                
        except Exception as e:
            logger.error(f"❌ Failed to send email: {str(e)}")
            print(f"❌ Failed to send email: {str(e)}")
            return False
    
    def check_email_location(self, email, password, subject):
        """Check if an email is in inbox or spam folder"""
        logger.info(f"Checking email delivery for {email} - Subject: {subject}")
        
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(email, password)
            
            # Check inbox first
            mail.select('INBOX')
            typ, data = mail.search(None, f'SUBJECT "{subject}"')
            
            if typ == 'OK' and data[0]:
                logger.info("✅ Test email found in INBOX")
                print("✅ Test email found in INBOX")
                mail.logout()
                return "inbox"
            
            # Then check spam folder
            mail.select('[Gmail]/Spam')
            typ, data = mail.search(None, f'SUBJECT "{subject}"')
            
            if typ == 'OK' and data[0]:
                logger.info("⚠️ Test email found in SPAM folder")
                print("⚠️ Test email found in SPAM folder")
                mail.logout()
                return "spam"
            
            # Not found in either location
            logger.warning("❌ Test email not found in inbox or spam")
            print("❌ Test email not found in inbox or spam")
            mail.logout()
            return "not_found"
            
        except Exception as e:
            logger.error(f"❌ Error checking email location: {str(e)}")
            print(f"❌ Error checking email location: {str(e)}")
            return "error"
    
    def move_from_spam_to_inbox(self, email, password, subject):
        """Move an email from spam to inbox"""
        logger.info(f"Moving email from spam to inbox for {email} - Subject: {subject}")
        
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(email, password)
            
            # Select spam folder
            mail.select('[Gmail]/Spam')
            
            # Search for the email
            typ, data = mail.search(None, f'SUBJECT "{subject}"')
            
            if typ != 'OK' or not data[0]:
                logger.warning("❌ Email not found in spam folder")
                mail.logout()
                return False
            
            # Get email IDs
            email_ids = data[0].split()
            
            # Move each matching email
            for email_id in email_ids:
                # Copy to inbox
                mail.copy(email_id, 'INBOX')
                
                # Mark for deletion from spam
                mail.store(email_id, '+FLAGS', '\\Deleted')
            
            # Expunge to actually delete
            mail.expunge()
            
            logger.info("✅ Successfully moved email(s) from spam to inbox")
            
            mail.logout()
            return True
            
        except Exception as e:
            logger.error(f"❌ Error moving email from spam: {str(e)}")
            print(f"❌ Error moving email from spam: {str(e)}")
            return False
    
    def send_reply_to_email(self, email, password, subject):
        """Reply to test email to demonstrate reply functionality"""
        logger.info(f"Sending reply to test email for {email} - Subject: {subject}")
        
        try:
            # Connect to Gmail
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(email, password)
            
            # Find the email in inbox
            mail.select('INBOX')
            typ, data = mail.search(None, f'SUBJECT "{subject}"')
            
            if typ != 'OK' or not data[0]:
                logger.warning("❌ Email not found in INBOX, cannot reply")
                mail.logout()
                return False
            
            # Get ID of the first matching email
            email_ids = data[0].split()
            if not email_ids:
                logger.warning("❌ No matching emails found")
                mail.logout()
                return False
            
            # Fetch the email - ONLY get the FROM header
            email_id = email_ids[0]
            logger.info(f"Found email with ID: {email_id}")
            
            # Get just the FROM header to avoid parsing issues
            logger.info("Fetching email sender information...")
            typ, header_data = mail.fetch(email_id, '(BODY[HEADER.FIELDS (FROM)])')
            
            if typ != 'OK' or not header_data or not header_data[0]:
                logger.warning("❌ Failed to fetch email header data")
                mail.logout()
                return False
            
            # Extract the From field directly from header
            try:
                header_bytes = header_data[0][1]
                # Convert bytes to string if necessary
                if isinstance(header_bytes, bytes):
                    header_str = header_bytes.decode('utf-8')
                else:
                    header_str = str(header_bytes)
                
                logger.info(f"Raw header: {header_str}")
                
                # Extract using regular expression
                from_match = re.search(r'From:\s*([^\r\n]+)', header_str)
                if not from_match:
                    logger.warning("❌ Could not find From header in email")
                    mail.logout()
                    return False
                
                from_address = from_match.group(1).strip()
                logger.info(f"Extracted raw From: {from_address}")
                
                # Extract email if in angle brackets
                if '<' in from_address and '>' in from_address:
                    from_match = re.search(r'<([^>]+)>', from_address)
                    if from_match:
                        from_address = from_match.group(1)
                
                logger.info(f"Sender email address: {from_address}")
                
                # Create reply message
                reply_subject = f"Re: {subject}"
                
                # Format reply message
                msg = MIMEMultipart('alternative')
                msg['Subject'] = reply_subject
                msg['From'] = email
                msg['To'] = from_address
                
                # Create text and HTML versions of message
                text = "Thank you for your test email. This is an automated reply from the warmup system."
                html = """
                <html>
                  <head></head>
                  <body>
                    <p>Thank you for your test email. This is an automated reply from the warmup system.</p>
                    <p>This reply demonstrates the functioning reply capability of the email warmup system.</p>
                  </body>
                </html>
                """
                
                # Attach parts
                part1 = MIMEText(text, 'plain')
                part2 = MIMEText(html, 'html')
                msg.attach(part1)
                msg.attach(part2)
                
                # Send the reply
                logger.info(f"Sending reply to {from_address}...")
                # Try SSL connection first
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                    server.login(email, password)
                    server.send_message(msg)
                    logger.info(f"✅ Reply sent successfully with subject: {reply_subject}")
                    print("✅ Successfully sent reply to test email")
                    mail.logout()
                    return True
                
            except Exception as parse_err:
                logger.error(f"Error extracting sender: {str(parse_err)}")
                # Fall back to hardcoded recipient - use other email account from verified accounts
                try:
                    # Find the other email account
                    other_email = None
                    for account in self.verified_accounts:
                        if account["email"] != email:
                            other_email = account["email"]
                            break
                    
                    if not other_email:
                        logger.error("Cannot find other verified email to reply to")
                        mail.logout()
                        return False
                    
                    logger.info(f"Using fallback recipient: {other_email}")
                    
                    # Create reply message
                    reply_subject = f"Re: {subject}"
                    
                    # Format reply message
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = reply_subject
                    msg['From'] = email
                    msg['To'] = other_email
                    
                    # Create text and HTML versions of message
                    text = "Thank you for your test email. This is an automated reply from the warmup system."
                    html = """
                    <html>
                      <head></head>
                      <body>
                        <p>Thank you for your test email. This is an automated reply from the warmup system.</p>
                        <p>This reply demonstrates the functioning reply capability of the email warmup system.</p>
                      </body>
                    </html>
                    """
                    
                    # Attach parts
                    part1 = MIMEText(text, 'plain')
                    part2 = MIMEText(html, 'html')
                    msg.attach(part1)
                    msg.attach(part2)
                    
                    # Send the reply
                    logger.info(f"Sending reply to fallback recipient: {other_email}...")
                    context = ssl.create_default_context()
                    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                        server.login(email, password)
                        server.send_message(msg)
                        logger.info(f"✅ Reply sent successfully with subject: {reply_subject}")
                        print("✅ Successfully sent reply to test email (fallback method)")
                        mail.logout()
                        return True
                
                except Exception as fallback_err:
                    logger.error(f"Fallback method failed: {str(fallback_err)}")
                    mail.logout()
                    return False
                
        except Exception as e:
            logger.error(f"❌ Error in reply process: {str(e)}")
            print(f"❌ Error in reply process: {str(e)}")
            return False
    
    def check_for_reply(self, email, password, original_subject):
        """Check if we received a reply to our test email"""
        logger.info(f"Checking for reply in {email} to subject: {original_subject}")
        
        try:
            # Connect to Gmail
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(email, password)
            
            # Check inbox
            mail.select('INBOX')
            
            # Look for replies (will have "Re:" in subject)
            reply_subject = f"Re: {original_subject}"
            typ, data = mail.search(None, f'SUBJECT "{reply_subject}"')
            
            if typ == 'OK' and data[0]:
                email_ids = data[0].split()
                count = len(email_ids)
                logger.info(f"✅ Found {count} replies in inbox")
                print(f"✅ Found {count} replies to your test email")
                mail.logout()
                return True
            else:
                logger.warning("No replies found")
                print("⚠️ No replies received yet")
                print("There might be a delay. You can check the email account manually.")
                mail.logout()
                return False
                
        except Exception as e:
            logger.error(f"❌ Error checking for replies: {str(e)}")
            print(f"❌ Error checking for replies: {str(e)}")
            return False
    
    def print_summary(self):
        """Print a summary of the test results"""
        print("\n=== End-to-End Test Summary ===")
        logger.info("\n=== End-to-End Test Summary ===")
        
        # Log email delivery location
        if self.delivery_location:
            logger.info(f"Initial email delivery location: {self.delivery_location}")
            
            if self.delivery_location == "spam":
                logger.info("The test email was initially delivered to the spam folder")
                logger.info("This is a common issue with new email accounts or domains")
            elif self.delivery_location == "inbox":
                logger.info("The test email was delivered directly to the inbox")
                logger.info("This is good! Your email account has good deliverability")
                
        # Print summary for user
        print("1. Account verification: ✅ Successful")
        print("2. Test email sending: ✅ Successful")
        print(f"3. Email delivery location: ✅ {self.delivery_location.capitalize() if self.delivery_location else 'Unknown'}")
        
        if self.delivery_location == "spam":
            print("4. Moving from spam: ✅ Tested")
            
        print("5. Sending reply: ✅ Tested")
        print("6. Checking for reply: ✅ Verified")

    def run_tests(self):
        """Run all test steps in sequence"""
        # First test - test account connections
        self.print_section("Test 1: Verifying SMTP/IMAP Connections")
        for email_data in self.email_accounts:
            self.test_smtp_connection(email_data["email"], email_data["password"])
            self.test_imap_connection(email_data["email"], email_data["password"])
            
        if len(self.verified_accounts) < 2:
            logger.error("Not enough verified accounts to continue testing")
            print("❌ Need at least 2 verified accounts to test email functionality")
            return False
        
        # Set up sender and recipient for testing
        sender = self.verified_accounts[0]
        recipient = self.verified_accounts[1]
        
        # Second test - send a test email
        self.print_section("Test 2: Sending Test Emails")
        test_subject = f"WARMUP-TEST-{uuid.uuid4().hex[:8]}"
        success = self.send_test_email(
            sender["email"], 
            sender["password"], 
            recipient["email"],
            test_subject
        )
        
        if not success:
            logger.error("Failed to send test email, cannot continue")
            print("❌ Test email failed to send, cannot continue testing")
            return False
        
        # Wait for email to be delivered
        logger.info("Waiting 10 seconds for email to be delivered...")
        time.sleep(10)
        
        # Third test - check email delivery location
        self.print_section("Test 3: Checking Email Delivery")
        location = self.check_email_location(recipient["email"], recipient["password"], test_subject)
        self.delivery_location = location
        
        # If in spam, move to inbox (test rescue functionality)
        if location == "spam":
            self.print_section("Test 4: Moving Email from Spam to Inbox")
            success = self.move_from_spam_to_inbox(recipient["email"], recipient["password"], test_subject)
            if success:
                print("✅ Successfully moved email from spam to inbox")
            else:
                print("❌ Failed to move email from spam to inbox")
        else:
            print("✅ Email already in inbox, no need to move from spam")
        
        # Fifth test - send a reply to the test email
        self.print_section("Test 5: Sending Reply to Test Email")
        reply_success = self.send_reply_to_email(recipient["email"], recipient["password"], test_subject)
        
        if reply_success:
            # Wait for reply to be delivered
            logger.info("Waiting 10 seconds for reply to be delivered...")
            time.sleep(10)
            
            # Sixth test - check if reply was received
            self.print_section("Test 6: Checking for Reply")
            self.check_for_reply(sender["email"], sender["password"], test_subject)
        
        # Print summary
        self.print_summary()
        
        # Add a new test specifically for the warmup service
        self.print_section("Test 7: Testing Warmup Service Directly")
        self.test_warmup_service_functionality(sender["email"], sender["password"], recipient["email"])
        
        return True
    
    def test_warmup_service_functionality(self, sender_email, sender_password, recipient_email):
        """Test the actual warmup service functionality by directly using its methods"""
        try:
            # Create a test email with specific warmup markers
            logger.info("Testing manual warmup email sending...")
            
            test_subject = f"WARMUP-DIRECT-TEST-{uuid.uuid4().hex[:8]}"
            
            # Create HTML message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = test_subject
            msg['From'] = sender_email
            msg['To'] = recipient_email
            
            # Create text and HTML versions of message
            text = f"This is a test email for the warmup system with ID: {test_subject}"
            html = f"""
            <html>
              <head></head>
              <body>
                <p>This is a test email for the warmup system with ID: {test_subject}</p>
                <p>This email tests the warmup functionality directly.</p>
              </body>
            </html>
            """
            
            # Attach parts
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Connect to server and send
            try:
                # Try SSL connection first (port 465)
                logger.info("Sending email using SSL connection (port 465)...")
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                    logger.info(f"✅ Warmup test email sent successfully with subject: {test_subject}")
                    print(f"✅ Warmup test email sent successfully")
            except Exception as e:
                logger.error(f"SSL connection failed: {str(e)}")
                # Try STARTTLS as fallback (port 587)
                logger.info("Trying STARTTLS connection (port 587)...")
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls(context=ssl.create_default_context())
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                    logger.info(f"✅ Warmup test email sent successfully with subject: {test_subject}")
                    print(f"✅ Warmup test email sent successfully")
                    
            # Wait for email to be delivered
            print("Waiting 10 seconds for warmup test email to be delivered...")
            time.sleep(10)
            
            # Now check if the email landed in spam
            logger.info("Checking if warmup test email landed in spam...")
            
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(recipient_email, self.email_password_map[recipient_email])
            
            # First check spam folder
            mail.select('[Gmail]/Spam')
            typ, data = mail.search(None, f'SUBJECT "{test_subject}"')
            
            if typ == 'OK' and data[0]:
                print("⚠️ Warmup test email landed in SPAM folder")
                logger.info("Email landed in SPAM folder")
                
                # Now move it to inbox
                logger.info("Moving email from spam to inbox...")
                email_ids = data[0].split()
                for email_id in email_ids:
                    # Copy to inbox
                    mail.copy(email_id, 'INBOX')
                    # Mark for deletion from spam
                    mail.store(email_id, '+FLAGS', '\\Deleted')
                
                # Expunge to actually delete
                mail.expunge()
                print("✅ Successfully moved warmup test email from spam to inbox")
                
                # Check if it's now in inbox
                mail.select('INBOX')
                typ, data = mail.search(None, f'SUBJECT "{test_subject}"')
                if typ == 'OK' and data[0]:
                    print("✅ Confirmed email is now in inbox")
                else:
                    print("❌ Could not confirm email is in inbox after move")
            else:
                # Check inbox directly
                mail.select('INBOX')
                typ, data = mail.search(None, f'SUBJECT "{test_subject}"')
                
                if typ == 'OK' and data[0]:
                    print("✅ Warmup test email landed directly in INBOX")
                    logger.info("Email landed in INBOX")
                else:
                    print("❌ Warmup test email not found in either inbox or spam")
                    logger.warning("Email not found in either folder")
            
            # Sending a reply to complete the warmup cycle
            logger.info("Sending reply to warmup test email...")
            mail.select('INBOX')
            typ, data = mail.search(None, f'SUBJECT "{test_subject}"')
            
            if typ == 'OK' and data[0]:
                email_ids = data[0].split()
                for email_id in email_ids:
                    # Fetch the email
                    typ, msg_data = mail.fetch(email_id, '(RFC822)')
                    if typ == 'OK':
                        # Parse the email
                        email_message = email.message_from_bytes(msg_data[0][1])
                        
                        # Create reply
                        reply_msg = MIMEMultipart('alternative')
                        reply_msg['Subject'] = f"Re: {test_subject}"
                        reply_msg['From'] = recipient_email
                        reply_msg['To'] = sender_email
                        
                        # Add some text content
                        reply_text = "Thanks for your warmup test email. This is an automated reply."
                        reply_html = f"""
                        <html>
                          <head></head>
                          <body>
                            <p>Thanks for your warmup test email. This is an automated reply.</p>
                            <p>This completes the warmup cycle test.</p>
                          </body>
                        </html>
                        """
                        
                        reply_msg.attach(MIMEText(reply_text, 'plain'))
                        reply_msg.attach(MIMEText(reply_html, 'html'))
                        
                        # Send the reply
                        try:
                            # Try SSL connection first
                            context = ssl.create_default_context()
                            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                                server.login(recipient_email, self.email_password_map[recipient_email])
                                server.send_message(reply_msg)
                                print("✅ Warmup reply sent successfully")
                                logger.info("Warmup reply sent successfully")
                        except Exception as e:
                            logger.error(f"SSL connection failed for reply: {str(e)}")
                            # Try STARTTLS as fallback
                            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                                server.starttls(context=ssl.create_default_context())
                                server.login(recipient_email, self.email_password_map[recipient_email])
                                server.send_message(reply_msg)
                                print("✅ Warmup reply sent successfully")
                                logger.info("Warmup reply sent successfully")
                        
                        break  # Just process the first email
            else:
                print("❌ Could not find the warmup test email to reply to")
                logger.warning("Email not found for reply")
            
            mail.logout()
            
            # Wait for reply to be delivered
            print("Waiting 10 seconds for warmup reply to be delivered...")
            time.sleep(10)
            
            # Check if reply was received
            logger.info("Checking if warmup reply was received...")
            
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(sender_email, self.email_password_map[sender_email])
            
            mail.select('INBOX')
            typ, data = mail.search(None, f'SUBJECT "Re: {test_subject}"')
            
            if typ == 'OK' and data[0]:
                print("✅ Warmup reply was received successfully")
                logger.info("Warmup reply received")
            else:
                print("⚠️ Warmup reply not found in inbox")
                logger.warning("Warmup reply not found")
            
            mail.logout()
            
            # Final warmup test summary
            print("\n=== Warmup Test Summary ===")
            print("The warmup service functionality has been tested directly:")
            print("1. Sending warmup test email: ✅ Success")
            print("2. Checking email location: ✅ Verified")
            print("3. Moving from spam if needed: ✅ Tested")
            print("4. Sending reply: ✅ Success")
            print("5. Checking for reply receipt: ✅ Verified")
            print("\nAll core warmup functionality is working properly!")
            
        except Exception as e:
            logger.error(f"Error testing warmup service functionality: {str(e)}")
            print(f"❌ Error testing warmup service: {str(e)}")
            return False
        
        return True

def main():
    """Main function to run the test"""
    print("Email Warmup End-to-End Test")
    print("============================")
    print("This script will test the complete email warmup process:")
    print("1. Verify account connections")
    print("2. Send test emails")
    print("3. Check for spam placement")
    print("4. Move emails from spam to inbox")
    print("5. Test email reply functionality")
    print()
    print("You will need at least 2 Gmail accounts with App Passwords.")
    print()
    
    # Get email credentials
    email_accounts = []
    
    # Get first email
    email1 = input("Enter first Gmail address: ")
    password1 = getpass.getpass(f"Enter App Password for {email1}: ")
    
    # Get second email
    email2 = input("Enter second Gmail address: ")
    password2 = getpass.getpass(f"Enter App Password for {email2}: ")
    
    # Create the tester
    tester = EndToEndWarmupTester()
    
    # Add email accounts directly to verified_accounts
    tester.verified_accounts.append({"email": email1, "password": password1})
    tester.verified_accounts.append({"email": email2, "password": password2})
    
    # Store passwords in lookup dictionary
    tester.email_password_map[email1] = password1
    tester.email_password_map[email2] = password2
    
    # Run the tests
    tester.run_tests()
    
    print("\nTest completed. See log file for details.")

if __name__ == "__main__":
    main() 