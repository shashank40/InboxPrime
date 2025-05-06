#!/usr/bin/env python3
import smtplib
import imaplib
import ssl
import getpass
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import uuid

def test_send_email(sender_email, sender_password, recipient_email):
    """Test sending an email directly using standard smtplib"""
    print(f"\n--- Testing sending email from {sender_email} to {recipient_email} ---")
    
    # Create message
    msg = MIMEMultipart('alternative')
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"TEST-EMAIL-{uuid.uuid4().hex[:8]}"
    
    # Add body
    text = "This is a test email sent from the email warmup test script."
    html = f"""
    <html>
      <body>
        <p>This is a test email sent from the email warmup test script.</p>
        <p>Test ID: {uuid.uuid4().hex[:8]}</p>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))
    
    # Connect to server
    try:
        # Create a secure SSL context
        context = ssl.create_default_context()
        
        # Try SSL method first (port 465)
        try:
            print("Trying SSL connection (port 465)...")
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                # Login
                server.login(sender_email, sender_password)
                
                # Send email
                server.sendmail(sender_email, recipient_email, msg.as_string())
                print("✅ Email sent successfully using SSL (port 465)")
                return True
        except Exception as e:
            print(f"❌ SSL connection failed: {str(e)}")
            print("Trying STARTTLS connection (port 587)...")
            
            # Try STARTTLS method (port 587)
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.ehlo()  # Can be omitted
                server.starttls(context=context)
                server.ehlo()  # Can be omitted
                
                # Login
                server.login(sender_email, sender_password)
                
                # Send email
                server.sendmail(sender_email, recipient_email, msg.as_string())
                print("✅ Email sent successfully using STARTTLS (port 587)")
                return True
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        return False

def test_check_inbox(email_address, password, look_for="TEST-EMAIL-"):
    """Test checking inbox using standard imaplib"""
    print(f"\n--- Testing IMAP connection to {email_address} ---")
    try:
        # Connect to server
        print("Connecting to IMAP server...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        
        # Login
        print("Logging in...")
        mail.login(email_address, password)
        
        # List all folders
        print("Listing all folders...")
        type, data = mail.list()
        folders = []
        for folder in data:
            folder_name = folder.decode().split(' "/" ')[1].strip('"')
            folders.append(folder_name)
        
        print(f"Found {len(folders)} folders: {', '.join(folders[:5])}{'...' if len(folders) > 5 else ''}")
        
        # Check specific important Gmail folders
        gmail_folders = ["INBOX", "[Gmail]/All Mail", "[Gmail]/Spam", "[Gmail]/Trash", 
                          "[Gmail]/Sent Mail", "[Gmail]/Important", "[Gmail]/Promotions"]
        
        found_emails = []
        
        # Search for test emails in each folder
        for folder in folders:
            try:
                print(f"Checking folder: {folder}")
                mail.select(folder)
                
                # Search for test emails
                result, data = mail.search(None, f'SUBJECT "{look_for}"')
                
                if result == 'OK':
                    email_ids = data[0].split()
                    if email_ids:
                        print(f"  ✅ Found {len(email_ids)} test emails in {folder}")
                        
                        # Fetch the latest one
                        latest_email_id = email_ids[-1]
                        result, data = mail.fetch(latest_email_id, "(RFC822)")
                        raw_email = data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        print(f"  Latest test email: {msg['Subject']}")
                        found_emails.append((folder, msg['Subject']))
                    else:
                        print(f"  No test emails found in {folder}")
            except Exception as e:
                print(f"  Error checking folder {folder}: {str(e)}")
        
        if found_emails:
            print("\nSummary of found test emails:")
            for folder, subject in found_emails:
                print(f"- {subject} (in {folder})")
        else:
            print("\n❌ No test emails found in any folder")
        
        # Logout
        mail.logout()
        return True
    except Exception as e:
        print(f"❌ Failed to check inbox: {str(e)}")
        return False

def move_from_spam_and_reply(email_address, password, look_for="TEST-EMAIL-"):
    """Find test emails in spam, move them to inbox, and reply to them"""
    print(f"\n--- Moving emails from spam to inbox and sending replies ---")
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_address, password)
        
        # Try to select spam folder
        spam_folders = ["[Gmail]/Spam", "Spam", "Junk"]
        spam_folder = None
        
        for folder in spam_folders:
            result = mail.select(folder)
            if result[0] == 'OK':
                spam_folder = folder
                print(f"✅ Found spam folder: {spam_folder}")
                break
        
        if not spam_folder:
            print("❌ Could not find spam folder")
            return False
        
        # Search for test emails in spam
        typ, data = mail.search(None, f'SUBJECT "{look_for}"')
        
        if typ != 'OK':
            print("❌ Search failed")
            return False
        
        email_ids = data[0].split()
        count = len(email_ids)
        
        if count == 0:
            print("❌ No test emails found in spam")
            return False
        
        print(f"✅ Found {count} test emails in spam")
        
        # Move each email to inbox and reply
        moved_count = 0
        replied_count = 0
        
        for email_id in email_ids:
            # Get email content
            typ, data = mail.fetch(email_id, '(RFC822)')
            if typ != 'OK':
                print(f"❌ Failed to fetch email {email_id}")
                continue
            
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Move to inbox
            result = mail.copy(email_id, 'INBOX')
            if result[0] == 'OK':
                mail.store(email_id, '+FLAGS', '\\Deleted')
                mail.expunge()
                moved_count += 1
                print(f"✅ Moved email '{msg['Subject']}' from spam to inbox")
            else:
                print(f"❌ Failed to move email '{msg['Subject']}' to inbox")
                continue
        
        print(f"✅ Moved {moved_count} emails from spam to inbox")
        
        # Now reply to emails in inbox
        mail.select('INBOX')
        typ, data = mail.search(None, f'SUBJECT "{look_for}"')
        
        if typ != 'OK':
            print("❌ Search in inbox failed")
            return False
        
        email_ids = data[0].split()
        
        for email_id in email_ids:
            # Get email content
            typ, data = mail.fetch(email_id, '(RFC822)')
            if typ != 'OK':
                continue
                
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Get sender information
            sender = msg['From']
            if '<' in sender:
                sender = sender.split('<')[1].split('>')[0]
            
            # Create reply
            reply_msg = MIMEMultipart('alternative')
            reply_msg['From'] = email_address
            reply_msg['To'] = sender
            reply_msg['Subject'] = f"Re: {msg['Subject']}"
            reply_msg['In-Reply-To'] = msg['Message-ID']
            reply_msg['References'] = msg['Message-ID']
            
            # Add reply content
            reply_text = f"This is a test reply to your email. Thanks for sending the test email!"
            reply_html = f"""
            <html>
              <body>
                <p>This is a test reply to your email.</p>
                <p>Thanks for sending the test email!</p>
                <p>Reply ID: {uuid.uuid4().hex[:8]}</p>
              </body>
            </html>
            """
            
            reply_msg.attach(MIMEText(reply_text, 'plain'))
            reply_msg.attach(MIMEText(reply_html, 'html'))
            
            # Send reply
            try:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                    server.login(email_address, password)
                    server.sendmail(email_address, sender, reply_msg.as_string())
                    replied_count += 1
                    print(f"✅ Sent reply to '{msg['Subject']}'")
            except Exception as e:
                print(f"❌ Failed to send reply: {str(e)}")
        
        print(f"✅ Sent {replied_count} replies")
        
        # Logout
        mail.close()
        mail.logout()
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    print("Direct Email Test")
    print("================")
    print("This script will test sending emails directly with smtplib/imaplib")
    print("You need to use App Passwords for Gmail accounts.")
    print("\nOptions:")
    print("1. Send test email and check inbox")
    print("2. Move emails from spam to inbox and reply")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ")
    
    if choice == "1":
        # Get credentials
        sender_email = input("Enter sender Gmail address: ")
        sender_password = getpass.getpass("Enter sender App Password: ")
        recipient_email = input("Enter recipient Gmail address: ")
        
        # Remove any spaces from password
        sender_password = sender_password.replace(" ", "")
        
        # Test sending
        if test_send_email(sender_email, sender_password, recipient_email):
            print("\nWaiting 10 seconds for email to be delivered...")
            time.sleep(10)
            
            # Now check inbox
            recipient_password = getpass.getpass(f"Enter recipient App Password for {recipient_email}: ")
            recipient_password = recipient_password.replace(" ", "")
            
            test_check_inbox(recipient_email, recipient_password)
    
    elif choice == "2":
        email_address = input("Enter Gmail address: ")
        password = getpass.getpass("Enter App Password: ")
        password = password.replace(" ", "")
        
        move_from_spam_and_reply(email_address, password)
    
    else:
        print("Exiting...")
        return
    
    print("\nTest completed.")

if __name__ == "__main__":
    main() 