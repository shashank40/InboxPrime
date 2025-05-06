# Testing Email Warmup with Gmail Accounts

This guide explains how to test the email warmup system using two Gmail accounts.

## Prerequisites

1. **Two Gmail accounts** with their respective passwords
2. **2-Step Verification** enabled on both accounts
3. **App Passwords** generated for both accounts

## Step 1: Enable 2-Step Verification

For each Gmail account:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Scroll to "How you sign in to Google"
3. Click on "2-Step Verification"
4. Follow the prompts to set up 2-Step Verification

## Step 2: Generate App Passwords

For each Gmail account:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Scroll to "How you sign in to Google"
3. Click on "App passwords" (only visible if 2-Step Verification is enabled)

   **Note**: If App passwords is not visible even after enabling 2-Step Verification:
   - Try accessing directly at: https://myaccount.google.com/apppasswords
   - Verify you're using a personal Google account (not a Workspace account)
   - Check if Advanced Protection Program is enabled on your account
   - Try using a different browser or clearing your cache
   - If using a Workspace account, check with your administrator if App passwords are allowed

4. Select "Mail" for the app and "Other" for the device
5. Enter "Email Warmup" as the name
6. Click "Generate"
7. **Copy the 16-character password** that appears (it looks like: xxxx xxxx xxxx xxxx)
8. **Save this password** - you won't be able to see it again and will need it for testing

### Detailed App Password Guide

If you're still having trouble generating or using App Passwords:

1. **Create App Password with these exact steps**:
   - Go to https://myaccount.google.com/
   - Click on "Security" in the left sidebar
   - Under "Signing in to Google," make sure 2-Step Verification is "ON"
   - Below that, click on "App passwords" (if you don't see this option, see troubleshooting below)
   - At the top of the App passwords page, select "Mail" from the "Select app" dropdown
   - Select "Other (Custom name)" from the "Select device" dropdown 
   - Enter "Email Warmup" as the name
   - Click the "GENERATE" button
   - Copy the entire 16-character code (remove spaces when using it)

2. **If App passwords is not visible**:
   - If you're using a company Google Workspace account, App passwords may be disabled by your admin
   - If you have Advanced Protection enabled on your account, App passwords may be unavailable
   - Some Google account types have restrictions on App passwords
   - Try creating a new personal Gmail account specifically for testing

3. **Alternative testing approach**:
   - If you absolutely cannot get App passwords working, try using an email provider that allows "Less secure app access" like Outlook.com
   - Our test script allows using any email provider, not just Gmail

## Step 3: Run the Test Script

1. Make sure the email warmup server is running:
   ```bash
   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

2. In a separate terminal, run the test script:
   ```bash
   python run_test.py
   ```

3. Follow the prompts to enter:
   - Whether to delete log files after testing
   - Username for registration/login
   - Your full name
   - First Gmail address
   - Second Gmail address
   - Password for authentication
   - App Password for the first Gmail account
   - App Password for the second Gmail account

## Step 4: Check Results

1. The script will output detailed logs to the console and a log file.
2. After the test completes, check both Gmail inboxes manually.
3. Look for emails with subjects containing "WARMUP-".
4. Check spam folders to ensure the emails are not landing there.

## Troubleshooting

If you encounter issues:

1. **Incorrect App Password**: Make sure you've entered the App Password correctly (all 16 characters, no spaces).
2. **Verification Errors**: Ensure 2-Step Verification is enabled and App Passwords are generated correctly.
3. **SMTP Connection Issues**: Check that port 465 isn't blocked by your network.
4. **API Connection Issues**: Ensure the server is running on port 8000.

### SMTP Authentication Troubleshooting

If you're having issues with Gmail SMTP authentication:

1. **Test Gmail connection independently**:
   ```bash
   python test_gmail_conn.py
   ```
   This script will test both SSL (port 465) and STARTTLS (port 587) connections.

2. **Try port 587 if port 465 fails**:
   Our system will automatically try both ports, but setting your configuration to use port 587 directly may help.

3. **Check your App Password**:
   - Make sure there are no spaces in your App Password
   - Generate a fresh App Password if needed
   - Enter exactly 16 characters

4. **Verify Gmail isn't blocking the connection**:
   - Check for security alerts in your Gmail account
   - Approve any new device notifications

5. **Network issues**:
   - Some networks block outgoing connections on ports 465 and 587
   - Try using a different network if possible

### Spam Placement Issues

When testing the email warmup system, you may find that emails are being sent but not appearing in the inbox. This is normal and expected during the initial warmup phase:

1. **Check the Spam folder**: 
   - Gmail and other providers often place emails from new senders in the Spam folder
   - The warmup system is designed to automatically detect and move emails from Spam to Inbox

2. **Train the spam filter**:
   - When you find warmup emails in spam, mark them as "Not Spam"
   - Reply to some of the emails to signal to Gmail that they're legitimate
   - Add the sender to your contacts

3. **Initial spam placement is normal**:
   - It's common for the first several days of warmup emails to be placed in spam
   - This is why email warmup is a gradual process that takes weeks, not days
   - The system gradually increases sending volume as deliverability improves

4. **Patience is key**:
   - Email warmup typically takes 3-4 weeks for optimal results
   - Gradually, more emails will be delivered to the inbox instead of spam
   - The system tracks spam placement metrics to monitor progress

5. **For testing purposes**:
   - You can use the `direct_email_test.py` script to check if emails are being delivered to spam

## Important Notes

- App Passwords should be treated as sensitive information.
- Each App Password can only be viewed once when created.
- You can revoke App Passwords at any time from your Google Account security settings.
- Gmail has sending limits (500 emails per day for regular accounts).

## Log Files Management

The test script creates log files with timestamps for each test run. You can manage these files in several ways:

1. **Delete logs after test completion**:
   - When running the test, respond "y" to the "Delete log files after test?" prompt
   - Log files will be automatically deleted if the test completes successfully

2. **Delete logs manually**:
   ```bash
   python run_test.py --clean
   ```
   This command deletes all email warmup test log files without running a new test.

3. **Delete specific log files**:
   ```bash
   rm email_warmup_test_*.log
   ```
   You can use this command to manually delete all log files.

Log files contain sensitive information like email addresses (but not passwords), so it's good practice to delete them after reviewing. 