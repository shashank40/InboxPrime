# Email Warmup Spam Handling & Reputation Building

This document explains how the email warmup system handles spam placement and builds sender reputation.

## Spam Detection & Handling

The email warmup system includes sophisticated spam handling to improve deliverability:

### 1. Automatic Spam Detection

The system automatically checks for warmup emails in:
- Regular inbox folders
- Spam/Junk folders (various names across email providers)
- Other Gmail-specific folders

When a warmup email is found in the spam folder, the system:
1. Logs the spam placement
2. Tracks the statistics for reporting
3. Moves the email from spam to inbox
4. Marks the email as rescued from spam

### 2. Spam Placement Metrics

The system tracks key spam handling metrics:
- **Spam placement rate**: Percentage of emails landing in spam
- **Inbox placement rate**: Percentage of emails landing in the inbox
- **Spam rescue rate**: Percentage of spam emails successfully moved to inbox

These metrics help you monitor the progress of your warmup campaign.

## Automatic Reply System

To build sender reputation, the system includes an intelligent reply mechanism:

### 1. Random Reply Selection

For regular inbox emails, the system:
- Uses a configurable reply rate (e.g., 40%)
- Randomly decides whether to reply to each email
- Creates a natural delay before replying to simulate human reading time

### 2. Prioritized Spam Replies

For emails found in spam, the system:
- Always attempts to reply (100% reply rate)
- Sends replies immediately to quickly build reputation
- Uses tailored reply content

Replying to spam-placed emails is particularly important for sender reputation as it signals to email providers that the communications are legitimate and desired.

## Configuration Options

These spam handling and reply features can be configured:

| Setting | Description | Default |
|---------|-------------|---------|
| `target_reply_rate` | Percentage of inbox emails to reply to | 40% |
| `read_delay_seconds` | Maximum time to wait before replying | 120 seconds |
| `randomize_volume` | Whether to vary sending volume | true |

## Monitoring & Reporting

The system generates detailed logs and reports about spam handling:

- **Dashboard statistics**: View spam placement and reply rates
- **Account-specific metrics**: Track progress for each email account
- **Daily logs**: Detailed information about each processed email

## Best Practices

To maximize the effectiveness of spam handling:

1. Run the warmup system consistently for at least 4 weeks
2. Monitor the spam placement rate - it should decrease over time
3. Allow automatic replies to build positive sender reputation
4. Manually check spam folders occasionally and mark emails as "Not Spam"
5. Add warmup senders to your contacts list

## Troubleshooting

If you experience persistent spam placement:

1. Check that your emails contain sufficient content and aren't too generic
2. Verify your DNS records (SPF, DKIM, DMARC) are properly configured
3. Ensure your email account isn't sending too many emails per day
4. Check that your IP address isn't on any blacklists 