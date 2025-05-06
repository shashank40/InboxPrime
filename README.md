# Email Warmup System

A robust email warmup system that helps improve email deliverability by gradually building sender reputation.

## What is Email Warmup?

Email warmup is the process of gradually building a positive sending reputation for new email accounts. When you start sending emails from a new account, email providers like Gmail and Outlook are cautious and may send your messages to spam folders.

This system helps by:
1. Sending a gradually increasing number of emails
2. Ensuring emails are opened and replied to
3. Moving emails out of spam folders automatically
4. Building sender reputation through engagement

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd email-warmup
```

2. Create a virtual environment with Python 3.9:
```bash
python3.9 -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with configuration:
```
DATABASE_URL=sqlite:///./email_warmup.db
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

5. Start the server:
```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Testing the System

The system includes several testing tools to verify its functionality:

### 1. End-to-End Test

The fastest way to test the complete system is using the end-to-end test script:

```bash
python test_end_to_end.py
```

#### How the End-to-End Test Works

The test follows these steps:

1. **Account Verification**: Tests SMTP and IMAP connections for your Gmail accounts
2. **Email Sending**: Sends a test email with a unique identifier from one account to another
3. **Delivery Detection**: Checks if the email landed in the inbox or spam folder
4. **Spam Handling**: If the email is in spam, it automatically moves it to the inbox
5. **Reply Process**: The recipient account sends a reply to the original email
6. **Reply Detection**: Verifies that the reply was received by the original sender
7. **Direct Warmup Test**: Tests the core warmup service functionality including spam detection and replies

This process tests all the key features of the email warmup system - sending emails, checking delivery location, handling spam, and building reputation through replies.

#### Test Results

When you run the end-to-end test, you'll see the system in action:

✅ **Working Gmail Connection**: The system verifies SMTP and IMAP connectivity  
✅ **Successful Email Delivery**: Test emails are sent and received correctly  
✅ **Spam Detection and Recovery**: The system detects if emails land in spam and rescues them  
✅ **Reply Functionality**: The system demonstrates sending replies to build reputation  
✅ **Robust Error Handling**: Automatic handling of connection errors and retries  

The test has been thoroughly verified to work with Gmail accounts. For best results, use App Passwords with Gmail for testing.

### Comprehensive System Test

For complete testing of all system features including metrics and API functionality, use the comprehensive test script:

```bash
python complete_system_test.py
```

This test:
1. Verifies server connection and API accessibility
2. Tests user registration and authentication
3. Creates and verifies email accounts
4. Configures and updates warmup settings
5. Runs the warmup process
6. Retrieves and validates metrics and statistics
7. Checks dashboard data and account history
8. Inspects database records for data integrity

This script is ideal for developers or users who want to validate every aspect of the system, including API endpoints, metrics collection, and database functionality.

### Additional Testing Tools

- **Direct Email Testing**: Test basic email sending and receiving
  ```bash
  python direct_email_test.py
  ```

- **Check Warmup Emails**: Scan accounts for all warmup emails
  ```bash
  python check_warmup_emails.py
  ```

- **API Testing**: Test the API with error handling
  ```bash
  python test_warmup_robust.py
  ```

## Key Files in this Repository

Here's a guide to the main files in this repository:

### Core System
- **main.py** - The main application entry point
- **app/** - Core application code (models, routes, services)
- **requirements.txt** - Package dependencies

### Testing Scripts
- **test_end_to_end.py** - Complete end-to-end test of email functionality
- **complete_system_test.py** - Comprehensive testing of API endpoints and metrics
- **direct_email_test.py** - Simple direct email testing
- **check_warmup_emails.py** - Tool to check for warmup emails in accounts
- **test_warmup_robust.py** - Tests API with better error handling

### Documentation
- **README.md** - This file, with system overview and instructions
- **SPAM_HANDLING.md** - Details on spam detection and handling functionality
- **GMAIL_TESTING.md** - Guide for setting up Gmail accounts for testing

## Setting Up Gmail Accounts for Testing

1. **Enable 2-Step Verification**:
   - Go to your Google Account > Security
   - Turn on 2-Step Verification

2. **Create an App Password**:
   - Go to your Google Account > Security > App passwords
   - Select "Mail" as the app and "Other" as the device
   - Enter a name like "Email Warmup"
   - Use the generated 16-character password in your tests

3. **SMTP and IMAP Settings**:
   ```
   SMTP Host: smtp.gmail.com
   SMTP Port: 465 (SSL) or 587 (STARTTLS)
   SMTP Username: your.email@gmail.com
   SMTP Password: your-app-password
   
   IMAP Host: imap.gmail.com
   IMAP Port: 993
   IMAP Username: your.email@gmail.com
   IMAP Password: your-app-password
   ```

For detailed instructions, see [Gmail Testing Guide](GMAIL_TESTING.md).

## How It Works

### Spam Detection and Handling

The system automatically:
1. Detects when emails land in spam folders
2. Moves these emails to the inbox
3. Prioritizes replying to emails that were in spam
4. Tracks spam placement rates over time

When the system detects a warmup email in a spam folder:
1. It immediately copies the email to the inbox
2. Removes the email from the spam folder
3. Marks the email as having been rescued from spam
4. Prioritizes sending a reply to this email (higher than normal reply rate)
5. The reply helps build sender reputation, telling email providers that these emails are wanted

This process is critical for building sender reputation and is one of the key features that improves deliverability over time.

For more details, see [Spam Handling & Reputation Building](SPAM_HANDLING.md).

### Best Practices for Email Warmup

- **Start Slow**: Begin with 2-4 emails per day
- **Gradual Increase**: Add 2-3 more emails every few days
- **Consistent Activity**: Send emails every day
- **Full Warmup Period**: Complete at least 4 weeks of warmup
- **Monitor Placement**: Check inbox vs. spam placement regularly

## API Documentation

When running the server, access the Swagger UI documentation at:
```
http://localhost:8000/docs
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 