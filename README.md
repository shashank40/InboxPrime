# Email Warmup API

A robust FastAPI-based backend for an email warmup system that helps improve email deliverability for marketing campaigns.

## Overview

Email Warmup API is designed to automatically warm up email accounts to improve deliverability. When new email accounts are used for marketing, they often end up in spam folders because they lack sender reputation. This system gradually builds reputation by:

1. Sending a gradually increasing number of emails from your account
2. Ensuring these emails are opened and replied to
3. Creating a natural sending pattern that email providers recognize as legitimate
4. Monitoring deliverability metrics to track progress

## Key Features

- **Multi-account Support**: Manage and warm up multiple email accounts simultaneously
- **Gradual Scaling**: Start with a few emails per day and gradually increase volume
- **Positive Engagement**: All warmup emails are opened and many are replied to
- **Domain Verification**: DNS validation for SPF, DKIM, and DMARC records
- **Deliverability Tracking**: Monitor inbox placement, open rates, and reply rates
- **Customizable Settings**: Configure warmup pace, volume, and other parameters
- **Dashboard & Analytics**: Track progress and performance metrics

## Best Practices for Email Warmup

Based on research and industry standards, here are the best practices for warming up email accounts:

1. **Start Slow**: Begin with just 2-4 emails per day
2. **Gradual Increase**: Add 2-3 more emails every few days
3. **Consistent Activity**: Send emails every day (or weekdays only if configured)
4. **Positive Engagement**: Ensure emails are opened and replied to (our system handles this)
5. **DNS Configuration**: Properly set up SPF, DKIM, and DMARC records (our system verifies this)
6. **Monitor Metrics**: Keep an eye on deliverability metrics, especially spam placement
7. **Full Warmup Period**: Complete at least 4 weeks of warmup before full-volume sending
8. **Continue Warmup**: Even after the initial period, keep some warmup activity ongoing

## Technical Architecture

- **Backend**: FastAPI (Python)
- **Database**: SQLAlchemy ORM with SQLite (configurable for other databases)
- **Authentication**: JWT-based token authentication
- **Email Interaction**: SMTP/IMAP for sending and receiving emails
- **Scheduling**: Background tasks for automated warmup cycles

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd email-warmup
```

2. Create a virtual environment with Python 3.9 and install dependencies:
```bash
# Make sure Python 3.9 is installed
python3.9 --version

# Create a virtual environment with Python 3.9
python3.9 -m venv venv

# Activate the virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

3. Create a `.env` file with configuration:
```
DATABASE_URL=sqlite:///./email_warmup.db
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

4. Run the application:
```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## API Documentation

Once the application is running, access the Swagger UI documentation at `http://localhost:8000/docs`.

Key endpoints include:

- **Authentication**
  - POST `/api/auth/register` - Register a new user
  - POST `/api/auth/token` - Get JWT token

- **Users**
  - GET `/api/users/me` - Get current user details
  - PUT `/api/users/me` - Update current user details

- **Email Accounts**
  - GET `/api/emails` - List email accounts
  - POST `/api/emails` - Add a new email account
  - PUT `/api/emails/{id}` - Update an email account
  - POST `/api/emails/{id}/verify` - Verify email credentials and DNS

- **Warmup**
  - GET `/api/warmup/configs` - List warmup configurations
  - PUT `/api/warmup/configs/{id}` - Update warmup configuration
  - POST `/api/warmup/run/{id}` - Manually run warmup for an account
  - GET `/api/warmup/status/{id}` - Get warmup status for an account
  - POST `/api/warmup/toggle/{id}` - Enable/disable warmup for an account

- **Dashboard**
  - GET `/api/dashboard/stats` - Get dashboard statistics
  - GET `/api/dashboard/history/{id}` - Get historical data for an account

## Schedule and Automation

The system automatically runs warmup cycles every 6 hours for all active and verified email accounts. You can also manually trigger warmup for specific accounts through the API.

The scheduler runs at:
- 00:00 UTC
- 06:00 UTC
- 12:00 UTC
- 18:00 UTC

## Why Email Warmup Works

Email service providers (like Gmail, Outlook, Yahoo) use sender reputation to determine if emails are legitimate. When you start sending emails from a new account, providers are cautious and may send your emails to spam.

By gradually increasing volume and ensuring positive engagement (opens and replies), you signal to these providers that your emails are wanted and legitimate. This builds your sender reputation over time.

The most important warmup signals are:
- Gradual increase in sending volume
- High open rates
- Good reply rates
- Low spam reports
- Proper DNS configuration (SPF, DKIM, DMARC)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Testing End-to-End with Real Email Accounts

This section provides detailed instructions for testing the email warmup system end-to-end using real email accounts. Following these steps will help you verify that the system is correctly warming up your email accounts to improve deliverability.

### Prerequisites

Before starting the testing process, you'll need:

1. **At least two email accounts** with SMTP and IMAP access enabled
   - Gmail accounts work well for testing (use App Passwords with 2-Step Verification)
   - Outlook/Office 365 accounts can also be used
   - For best results, use accounts from different providers (e.g., one Gmail and one Outlook)
   - For detailed setup instructions for Gmail, see [Gmail Testing Guide](GMAIL_TESTING.md)

2. **SMTP and IMAP credentials** for each account:
   - Email address
   - SMTP host, port, username, and password
   - IMAP host, port, username, and password

3. **The application running** with all dependencies installed as described in the [Installation](#installation) section

### Step 1: Set Up Email Accounts

1. **Register a user account** in the application:
   ```bash
   curl -X POST "http://localhost:8000/api/auth/register" \
     -H "Content-Type: application/json" \
     -d '{"email": "your-email@example.com", "username": "testuser", "password": "your-password", "full_name": "Test User"}'
   ```

2. **Get an authentication token**:
   ```bash
   curl -X POST "http://localhost:8000/api/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=testuser&password=your-password"
   ```
   Save the returned token for use in subsequent requests.

3. **Add your first email account**:
   ```bash
   curl -X POST "http://localhost:8000/api/emails" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "email_address": "your-email1@example.com",
       "display_name": "Your Name",
       "smtp_host": "smtp.gmail.com",
       "smtp_port": 587,
       "smtp_username": "your-email1@example.com",
       "smtp_password": "your-password",
       "imap_host": "imap.gmail.com",
       "imap_port": 993,
       "imap_username": "your-email1@example.com",
       "imap_password": "your-password",
       "domain": "example.com"
     }'
   ```
   Note the returned `id` value.

4. **Add your second email account** using the same method, but with the credentials for your second account.

5. **Verify the email accounts**:
   ```bash
   curl -X POST "http://localhost:8000/api/emails/{account_id}/verify" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```
   Replace `{account_id}` with the ID of each email account. This verifies that the SMTP and IMAP credentials work.

   Note: This step also checks for proper DNS records if you're using a custom domain. For testing purposes with Gmail or other public email providers, this step mainly verifies connectivity.

### Step 2: Configure Warmup Settings

1. **Create a warmup configuration** for each email account:
   ```bash
   curl -X POST "http://localhost:8000/api/warmup/configs" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "email_account_id": ACCOUNT_ID,
       "is_active": true,
       "max_emails_per_day": 30,
       "daily_increase": 2,
       "current_daily_limit": 2,
       "min_delay_seconds": 60,
       "max_delay_seconds": 300,
       "target_open_rate": 80,
       "target_reply_rate": 40,
       "warmup_days": 28,
       "weekdays_only": false,
       "randomize_volume": true,
       "read_delay_seconds": 120
     }'
   ```
   Replace `ACCOUNT_ID` with the ID of each email account.

### Step 3: Run the Warmup Process

1. **Manually trigger the warmup** process for each account:
   ```bash
   curl -X POST "http://localhost:8000/api/warmup/run/{account_id}" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```
   Replace `{account_id}` with the ID of each email account.

2. **Wait for the warmup process** to complete (approximately 5-10 minutes).

   Note: During initial testing, if you configured accounts with starting values of 2-3 emails per day, the system might not send any emails if you've already reached the daily limit in previous tests. Check the status response for "emails_sent" to confirm.

3. **Check the warmup status**:
   ```bash
   curl -X GET "http://localhost:8000/api/warmup/status/{account_id}" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```
   Replace `{account_id}` with the ID of each email account.

   The response will show details like:
   ```json
   {
     "success": true,
     "email_account_id": 1,
     "is_active": true,
     "current_daily_limit": 2,
     "days_in_warmup": 0,
     "warmup_progress": 0.0,
     "deliverability_score": 100.0,
     "open_rate": 0.0,
     "reply_rate": 0.0,
     "total_emails_sent": 0,
     "total_emails_received": 0
   }
   ```

### Step 4: Verify Results

1. **Check both email inboxes** manually:
   - You should see warmup emails with subjects containing "WARMUP-" in both inboxes
   - Emails should be automatically opened and some should be replied to

2. **Check spam folders** to ensure warmup emails are not landing in spam.

3. **Check the dashboard** for statistics:
   ```bash
   curl -X GET "http://localhost:8000/api/dashboard/stats" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

### Step 5: Automated Testing (Optional)

For more comprehensive testing, you can use the included test scripts:

1. **Use the API test script** to test the API endpoints:
   ```bash
   # Edit test_warmup.py to include your real email credentials
   python test_warmup.py
   ```

2. **Use the database test script** for lower-level testing:
   ```bash
   python test_db_warmup.py
   ```

### What to Look For

During the warmup process, you should observe:

1. **Gradual email sending**: The system starts with a low number of emails and gradually increases.

2. **Engagement metrics**: The system tracks open rates, reply rates, and deliverability scores.

3. **Automatic replies**: Some warmup emails should receive automatic replies.

4. **Inbox placement**: Emails should consistently land in the inbox, not spam.

### Troubleshooting

If you encounter issues during testing:

1. **Check the logs** for detailed error messages.

2. **Verify email credentials** are correct and that SMTP/IMAP access is enabled.

3. **Check firewall settings** if emails are not being sent or received.

4. **Verify account security settings** - some email providers may block automated access.

### Using Gmail Accounts for Testing

Gmail has specific security settings that need to be configured for SMTP/IMAP access:

1. **Enable 2-Step Verification**:
   - Go to your Google Account > Security
   - Turn on 2-Step Verification

2. **Create an App Password**:
   - Go to your Google Account > Security > App passwords
   - Select "Mail" as the app and "Other" as the device
   - Enter a name like "Email Warmup"
   - Copy the 16-character password that Google generates
   - Use this password in your SMTP/IMAP configuration (not your regular Gmail password)

3. **SMTP and IMAP Settings for Gmail**:
   ```
   SMTP Host: smtp.gmail.com
   SMTP Port: 587
   SMTP Username: your.email@gmail.com
   SMTP Password: your-app-password
   
   IMAP Host: imap.gmail.com
   IMAP Port: 993
   IMAP Username: your.email@gmail.com
   IMAP Password: your-app-password
   ```

4. **Check Gmail Filters**: Ensure you don't have filters that might move warmup emails to specific folders.

5. **Monitor Security Alerts**: Google may send security alerts about new app access. Confirm that these activities are authorized.

### Long-Term Warmup Strategy and Monitoring

For real-world email warmup over the recommended 4-week period:

1. **Gradual Progression**:
   - Week 1: 2-4 emails per day
   - Week 2: 5-10 emails per day
   - Week 3: 10-20 emails per day
   - Week 4: 20-30 emails per day

2. **Monitor Key Metrics** using the dashboard endpoints:
   ```bash
   # Get overall dashboard stats
   curl -X GET "http://localhost:8000/api/dashboard/stats" \
     -H "Authorization: Bearer YOUR_TOKEN"
   
   # Get historical data for specific account
   curl -X GET "http://localhost:8000/api/dashboard/history/{account_id}" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **Regular Status Checks**:
   - Check warmup status daily during the initial phase
   - Look for consistent inbox placement (not spam)
   - Ensure open rates remain above 80%
   - Monitor reply rates staying above 30-40%

4. **Adjust Configuration as Needed**:
   ```bash
   curl -X PUT "http://localhost:8000/api/warmup/configs/{account_id}" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "daily_increase": 3,
       "max_emails_per_day": 40
     }'
   ```

5. **Handling Issues**:
   - If emails start landing in spam, slow down the daily increase
   - If provider blocks access, verify security settings and possibly re-verify the account
   - For persistent delivery issues, consider adding proper DNS records (SPF, DKIM, DMARC)

6. **Transitioning to Production**:
   - After 4 weeks, your account should be well-warmed
   - Begin sending your actual marketing/transactional emails
   - Continue running warmup at a lower volume (5-10 emails per day) to maintain reputation

7. **Continuous Monitoring**:
   - Set up automated monitoring using the API
   - Schedule regular status checks via cron or scheduled tasks
   - Monitor for any sudden drops in deliverability scores

### Using the Swagger UI for Testing

Instead of using curl commands, you can use the built-in Swagger UI for a more user-friendly testing experience:

1. **Access the Swagger UI**:
   - Open your browser and go to `http://localhost:8000/docs`
   - You'll see a complete interactive API documentation
   - Note: Make sure to include trailing slashes for API endpoints if your browser requires them (e.g., `/api/auth/token/`)

2. **Authenticate**:
   - Scroll to the `/api/auth/token` endpoint
   - Click "Try it out"
   - Enter your username and password
   - Execute the request
   - Copy the token from the response
   - Click the "Authorize" button at the top of the page
   - Enter `Bearer YOUR_TOKEN` in the value field
   - Click "Authorize" to authenticate all future requests

3. **Add Email Accounts**:
   - Navigate to the `/api/emails` POST endpoint
   - Click "Try it out"
   - Enter your email account details in the request body
   - Execute the request
   - Note the returned account ID

4. **Verify Accounts**:
   - Navigate to the `/api/emails/{id}/verify` POST endpoint
   - Enter the account ID
   - Execute the request

5. **Create Warmup Configurations**:
   - Navigate to the `/api/warmup/configs` POST endpoint
   - Enter the warmup configuration with your account ID
   - Execute the request

6. **Run Warmup**:
   - Navigate to the `/api/warmup/run/{id}` POST endpoint
   - Enter the account ID
   - Execute the request

7. **Monitor Status**:
   - Navigate to the `/api/warmup/status/{id}` GET endpoint
   - Enter the account ID
   - Execute the request to view current warmup status

The Swagger UI makes it easy to explore all available endpoints and test them interactively without having to construct curl commands manually. 

## New Testing Script

### Run the new testing script

```bash
python run_test.py
```

This script automates the entire testing process with detailed logging, handles user registration, authentication, and account setup, and implements all steps: adding email accounts, verifying credentials, creating warmup configs, running warmups, waiting for them to complete, checking status, and prompting you to manually check the inboxes.

### Important Notes

1. **For Gmail, make sure you have 2-Step Verification and App Passwords set up**.
2. **For Outlook/eudia.com, verify your account settings allow app access**.
3. **You may need to check spam folders during testing**.
4. **The emails sent will have subjects containing "WARMUP-" for easy identification**.

This setup makes it simple to test both your email accounts with minimal effort while providing comprehensive logging for troubleshooting. 

## Local Testing with the Test Script

For quick and easy testing of your email warmup system, follow these simple steps:

### Prerequisites

1. **Two Gmail Accounts**: You need two Gmail accounts with the following setup:
   - 2-Step Verification enabled for both accounts
   - App Passwords generated for both accounts (regular passwords won't work)
   - For detailed instructions, see [Gmail Testing Guide](GMAIL_TESTING.md)

2. **Python Environment**: Make sure you've completed the steps in the [Installation](#installation) section to set up the Python environment with all required dependencies.

### Step 1: Start the Server

Run the server on localhost port 8000:

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Step 2: Run the Test Script

In a separate terminal window, run:

```bash
python run_test.py
```

### Step 3: Follow the Prompts

The script will ask you for:

1. Whether to delete log files after testing (y/n)
2. Username for registration/login (default: testuser)
3. Full name (default: Test User)
4. First Gmail address
5. Second Gmail address
6. Password for authentication (for system login)
7. App Password for first Gmail account (from Google Account > Security > App passwords)
8. App Password for second Gmail account

### Step 4: Wait for the Test to Complete

- The test will run for approximately 5 minutes
- It will register accounts, verify them, create warmup configurations, and run the warmup process
- You'll see detailed logs in the terminal and in a log file

### Step 5: Check Results

After the test completes:
- Check both Gmail inboxes for emails with subjects containing "WARMUP-"
- Check spam folders to ensure emails are not landing there
- Review the log file for detailed information on each step

### Troubleshooting

If you encounter a login error:
- Make sure the server is running properly
- Verify your username and password
- Check that you're using App Passwords (not regular passwords) for Gmail accounts

If email verification fails:
- Ensure 2-Step Verification is enabled and App Passwords are set up correctly
- Make sure you're entering the App Password without spaces
- Verify your Gmail accounts don't have additional security restrictions

### Cleaning Up

To delete all log files at any time:

```bash
python run_test.py --clean
```

This automated test script makes it easy to verify that your email warmup system is working correctly without having to manually set up accounts and configurations. 