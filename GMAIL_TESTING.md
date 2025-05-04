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
4. Select "Mail" for the app and "Other" for the device
5. Enter "Email Warmup" as the name
6. Click "Generate"
7. **Copy the 16-character password** that appears (it looks like: xxxx xxxx xxxx xxxx)
8. **Save this password** - you won't be able to see it again and will need it for testing

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