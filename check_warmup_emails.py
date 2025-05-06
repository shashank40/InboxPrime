#!/usr/bin/env python3
import imaplib
import email
import getpass
import sys
from datetime import datetime

def check_email_account(email_address, password, search_pattern="WARMUP-"):
    """Check a Gmail account for warmup emails in all folders"""
    print(f"\n==== Checking {email_address} for warmup emails ====")
    
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_address, password)
        print("✅ Successfully logged in")
        
        # Get list of all folders
        print("Listing all mail folders...")
        type, data = mail.list()
        
        if type != 'OK':
            print("❌ Failed to list folders")
            return False
            
        folders = []
        for item in data:
            decoded = item.decode()
            parts = decoded.split(' "')
            if len(parts) >= 2:
                folder = parts[-1].replace('"', '')
                folders.append(folder)
        
        print(f"Found {len(folders)} folders")
        
        # Explicitly check these important folders
        important_folders = ['INBOX', '[Gmail]/Spam', '[Gmail]/All Mail']
        for folder in important_folders:
            if folder not in folders:
                folders.append(folder)
        
        # Track stats
        total_warmup_emails = 0
        total_spam = 0
        inbox_count = 0
        
        # Check each folder
        for folder in folders:
            try:
                result = mail.select(folder)
                if result[0] != 'OK':
                    print(f"  ⚠️ Could not select folder: {folder}")
                    continue
                    
                # Search for emails with the warmup pattern in subject
                typ, data = mail.search(None, f'SUBJECT "{search_pattern}"')
                if typ != 'OK':
                    print(f"  ⚠️ Search failed in folder: {folder}")
                    continue
                
                email_ids = data[0].split()
                count = len(email_ids)
                
                if count > 0:
                    print(f"  📨 Found {count} warmup emails in {folder}")
                    total_warmup_emails += count
                    
                    if folder.lower() == 'inbox':
                        inbox_count = count
                    elif 'spam' in folder.lower():
                        total_spam = count
                    
                    # Get details of the most recent email
                    if email_ids:
                        latest_id = email_ids[-1]
                        typ, data = mail.fetch(latest_id, '(RFC822)')
                        if typ == 'OK':
                            msg = email.message_from_bytes(data[0][1])
                            print(f"    Latest: {msg['Subject']} from {msg['From']} on {msg['Date']}")
            except Exception as e:
                print(f"  ❌ Error checking folder {folder}: {str(e)}")
        
        mail.close()
        mail.logout()
        
        # Print summary
        print("\n=== Summary ===")
        print(f"Total warmup emails found: {total_warmup_emails}")
        print(f"Emails in Inbox: {inbox_count}")
        print(f"Emails in Spam: {total_spam}")
        
        if total_warmup_emails > 0:
            inbox_percent = (inbox_count / total_warmup_emails) * 100
            print(f"Inbox placement rate: {inbox_percent:.1f}%")
            print(f"Spam placement rate: {(total_spam / total_warmup_emails) * 100:.1f}%")
        
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Main function to run the email checker"""
    print("Warmup Email Checker")
    print("==================")
    print("This script checks Gmail accounts for warmup emails")
    print("You will need to use an App Password for each Gmail account")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Usage: python check_warmup_emails.py [email_address]")
        print("If email_address is provided, it will only check that account")
        print("Otherwise, it will prompt for multiple accounts")
        return
    
    accounts_to_check = []
    
    # Check if an email address was provided as an argument
    if len(sys.argv) > 1:
        email_address = sys.argv[1]
        password = getpass.getpass(f"Enter App Password for {email_address}: ")
        accounts_to_check.append((email_address, password.replace(" ", "")))
    else:
        # Ask for multiple accounts
        while True:
            email_address = input("Enter Gmail address (or press Enter to finish): ")
            if not email_address:
                break
                
            password = getpass.getpass(f"Enter App Password for {email_address}: ")
            accounts_to_check.append((email_address, password.replace(" ", "")))
    
    # Check each account
    for email_address, password in accounts_to_check:
        check_email_account(email_address, password)
    
    print("\nCheck completed.")

if __name__ == "__main__":
    main() 