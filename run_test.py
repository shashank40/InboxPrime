#!/usr/bin/env python3
"""
Simple wrapper script to test email warmup with specific accounts.

Usage:
  python run_test.py            # Run the test
  python run_test.py --clean    # Delete all log files
  
This script will test the email warmup system with two Gmail accounts.
Make sure you have created App Passwords for both accounts.
"""

import subprocess
import sys
import os
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Email Warmup Test Runner')
parser.add_argument('--clean', action='store_true', help='Delete all log files')
args = parser.parse_args()

# If clean flag is set, just delete logs and exit
if args.clean:
    print("Deleting all log files...")
    subprocess.run([sys.executable, "test_email_warmup.py", "--delete-logs"])
    sys.exit(0)

# Ensure test_email_warmup.py is in the current directory and executable
if not os.path.exists("test_email_warmup.py"):
    print("Error: test_email_warmup.py not found in the current directory.")
    print("Please run this script from the same directory as test_email_warmup.py.")
    sys.exit(1)

# Make the test script executable if it isn't already
if not os.access("test_email_warmup.py", os.X_OK):
    os.chmod("test_email_warmup.py", 0o755)

# Check if server is running
def check_server_running():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(("localhost", 8000))
        s.close()
        return True
    except:
        s.close()
        return False

if not check_server_running():
    print("Error: The email warmup server doesn't appear to be running.")
    print("Please start the server with: python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000")
    print("Then run this script again.")
    sys.exit(1)

# Run the test script with default arguments (will prompt for passwords)
print("Starting email warmup test with two Gmail accounts.")
print("\nIMPORTANT: You must use App Passwords, not regular Gmail passwords!")
print("Go to Google Account > Security > App passwords to generate App Passwords.")
print("\nYou will be prompted for your Gmail addresses and App Passwords.")
print("\nPress Ctrl+C at any time to cancel the test.")
print("\n" + "="*50)

try:
    # Ask if logs should be deleted after test
    delete_logs = input("Delete log files after test? (y/n): ").lower().startswith('y')
    
    # Custom username and name if desired
    username = input("Enter username for registration/login (default: testuser): ") or "testuser"
    name = input("Enter full name (default: Test User): ") or "Test User"
    
    # Get Gmail addresses
    email1 = input("Enter first Gmail address: ")
    email2 = input("Enter second Gmail address: ")
    
    if not email1 or not email2:
        print("Error: Both Gmail addresses are required.")
        sys.exit(1)
    
    if "@gmail.com" not in email1 or "@gmail.com" not in email2:
        print("Error: Both addresses must be Gmail addresses (ending with @gmail.com).")
        sys.exit(1)
    
    # Run the main test script
    cmd = [
        sys.executable, "test_email_warmup.py",
        "--username", username,
        "--name", name,
        "--email1", email1,
        "--email2", email2
    ]
    
    if delete_logs:
        cmd.append("--delete-logs")
    
    subprocess.run(cmd)
except KeyboardInterrupt:
    print("\nTest cancelled by user.")
    sys.exit(0)
except Exception as e:
    print(f"\nError: {str(e)}")
    sys.exit(1) 