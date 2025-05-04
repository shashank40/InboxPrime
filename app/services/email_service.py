import aiosmtplib
import aioimaplib
import asyncio
import ssl
import email.utils
import email.parser
import email.message
import uuid
import random
import logging
import re
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy.orm import Session
from app.models.models import EmailAccount, WarmupEmail, WarmupStat
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class EmailService:
    """Service for handling email operations"""
    
    @staticmethod
    async def verify_smtp_connection(email_account: EmailAccount) -> bool:
        """Verify SMTP connection credentials"""
        try:
            context = ssl.create_default_context()
            
            # Connect to the SMTP server
            if email_account.smtp_port == 465:
                # Port 465 uses SSL from the start
                smtp = aiosmtplib.SMTP_SSL(
                    hostname=email_account.smtp_host,
                    port=email_account.smtp_port,
                    ssl_context=context
                )
                await smtp.connect()
            else:
                # Port 587 uses STARTTLS
                smtp = aiosmtplib.SMTP(
                    hostname=email_account.smtp_host,
                    port=email_account.smtp_port,
                    use_tls=False
                )
                await smtp.connect()
                await smtp.starttls(tls_context=context)
            
            await smtp.login(email_account.smtp_username, email_account.smtp_password)
            await smtp.quit()
            return True
        except Exception as e:
            logger.error(f"SMTP verification failed: {str(e)}")
            return False
    
    @staticmethod
    async def verify_imap_connection(email_account: EmailAccount) -> bool:
        """Verify IMAP connection credentials"""
        try:
            # Connect to the IMAP server
            imap = aioimaplib.IMAP4_SSL(
                host=email_account.imap_host,
                port=email_account.imap_port
            )
            await imap.wait_hello_from_server()
            await imap.login(email_account.imap_username, email_account.imap_password)
            await imap.logout()
            return True
        except Exception as e:
            logger.error(f"IMAP verification failed: {str(e)}")
            return False
    
    @staticmethod
    async def send_email(
        sender: EmailAccount,
        recipient_email: str,
        subject: str,
        body_html: str,
        body_text: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Send an email and return success status, message, and message ID"""
        try:
            # Create message container
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{sender.display_name or sender.email_address} <{sender.email_address}>"
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg['Date'] = email.utils.formatdate(localtime=True)
            msg['Message-ID'] = f"<{uuid.uuid4()}@{sender.domain}>"
            
            # Attach parts
            msg.attach(MIMEText(body_text, 'plain'))
            msg.attach(MIMEText(body_html, 'html'))
            
            # Set up SSL context
            context = ssl.create_default_context()
            
            # Connect to the SMTP server
            if sender.smtp_port == 465:
                # Port 465 uses SSL from the start
                smtp = aiosmtplib.SMTP_SSL(
                    hostname=sender.smtp_host,
                    port=sender.smtp_port,
                    ssl_context=context
                )
                await smtp.connect()
            else:
                # Port 587 uses STARTTLS
                smtp = aiosmtplib.SMTP(
                    hostname=sender.smtp_host,
                    port=sender.smtp_port,
                    use_tls=False
                )
                await smtp.connect()
                await smtp.starttls(tls_context=context)
            
            # Send the email
            await smtp.login(sender.smtp_username, sender.smtp_password)
            await smtp.send_message(msg)
            await smtp.quit()
            
            return True, "Email sent successfully", msg['Message-ID']
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False, f"Failed to send email: {str(e)}", None
    
    @staticmethod
    async def check_inbox(
        email_account: EmailAccount,
        look_for_warmup_emails: bool = True,
        process_replies: bool = True
    ) -> Dict[str, Any]:
        """
        Check inbox for warmup emails and replies
        Returns a dictionary with statistics
        """
        stats = {
            "total": 0,
            "unread": 0,
            "warmup": 0,
            "warmup_replied": 0,
            "in_spam": 0,
            "processed": [],
            "errors": []
        }
        
        try:
            # Connect to the IMAP server
            imap = aioimaplib.IMAP4_SSL(
                host=email_account.imap_host,
                port=email_account.imap_port
            )
            await imap.wait_hello_from_server()
            await imap.login(email_account.imap_username, email_account.imap_password)
            
            # Check inbox
            await imap.select('INBOX')
            _, data = await imap.search('UTF-8', 'ALL')
            email_ids = data[0].split()
            stats["total"] = len(email_ids)
            
            # Check for unread emails
            _, data = await imap.search('UTF-8', 'UNSEEN')
            unread_ids = data[0].split()
            stats["unread"] = len(unread_ids)
            
            # If looking for warmup emails, process them
            if look_for_warmup_emails and email_ids:
                for email_id in email_ids:
                    try:
                        _, data = await imap.fetch(email_id, '(RFC822)')
                        raw_email = data[0][1]
                        
                        # Parse the email
                        msg = email.message_from_bytes(raw_email)
                        subject = msg.get('Subject', '')
                        
                        # Look for warmup email pattern
                        if 'WARMUP-' in subject:
                            stats["warmup"] += 1
                            
                            if process_replies:
                                # Mark as read
                                await imap.store(email_id, '+FLAGS', '\\Seen')
                                
                                # Append to processed list
                                stats["processed"].append({
                                    "message_id": msg.get('Message-ID', ''),
                                    "subject": subject,
                                    "from": msg.get('From', ''),
                                    "date": msg.get('Date', '')
                                })
                    except Exception as e:
                        stats["errors"].append(str(e))
            
            # Check spam folder for warmup emails
            await imap.select('[Gmail]/Spam')
            _, data = await imap.search('UTF-8', 'ALL')
            spam_ids = data[0].split()
            
            for email_id in spam_ids:
                try:
                    _, data = await imap.fetch(email_id, '(RFC822)')
                    raw_email = data[0][1]
                    
                    # Parse the email
                    msg = email.message_from_bytes(raw_email)
                    subject = msg.get('Subject', '')
                    
                    # Look for warmup email pattern
                    if 'WARMUP-' in subject:
                        stats["in_spam"] += 1
                        
                        if process_replies:
                            # Move to inbox
                            await imap.copy(email_id, 'INBOX')
                            await imap.store(email_id, '+FLAGS', '\\Deleted')
                            await imap.expunge()
                except Exception as e:
                    stats["errors"].append(str(e))
            
            # Logout
            await imap.logout()
            
            return stats
        except Exception as e:
            logger.error(f"Failed to check inbox: {str(e)}")
            stats["errors"].append(str(e))
            return stats
    
    @staticmethod
    async def generate_warmup_email(
        warmup_id: str, 
        is_reply: bool = False,
        reply_to_subject: str = None,
        reply_to_body: str = None
    ) -> Dict[str, str]:
        """Generate content for a warmup email"""
        
        # List of positive, casual business subjects
        subjects = [
            f"WARMUP-{warmup_id}: Quick question about your latest project",
            f"WARMUP-{warmup_id}: Touched base with the team",
            f"WARMUP-{warmup_id}: Following up on our conversation",
            f"WARMUP-{warmup_id}: Great insights from yesterday's call",
            f"WARMUP-{warmup_id}: Sharing some thoughts on the proposal",
            f"WARMUP-{warmup_id}: Article you might find interesting",
            f"WARMUP-{warmup_id}: Let's connect sometime this week",
            f"WARMUP-{warmup_id}: Quick update on the project status",
            f"WARMUP-{warmup_id}: Wanted to share some good news",
            f"WARMUP-{warmup_id}: Resources for our discussion"
        ]
        
        # List of positive, casual business email bodies
        bodies = [
            """
            <p>Hi there,</p>
            <p>Just wanted to share some quick thoughts on the project we discussed last week. I think we're making great progress, and the team is really coming together well.</p>
            <p>Let me know if you have any questions or if there's anything else you'd like to discuss!</p>
            <p>Best regards,<br>[Your Name]</p>
            """,
            """
            <p>Hello,</p>
            <p>I came across this interesting article that I thought might be relevant to our current project. It has some great insights that could be valuable for our approach.</p>
            <p>Looking forward to catching up soon!</p>
            <p>Warm regards,<br>[Your Name]</p>
            """,
            """
            <p>Hi,</p>
            <p>I wanted to follow up on our conversation from earlier this week. I've had some time to think about the points you raised, and I believe we're on the right track.</p>
            <p>Let's schedule a quick call if you'd like to discuss further.</p>
            <p>Thanks,<br>[Your Name]</p>
            """,
            """
            <p>Hello there,</p>
            <p>Just checking in to see how you're doing with the latest updates. Our team has been making steady progress, and I'm excited about where we're heading.</p>
            <p>Feel free to reach out if you need any clarification or support!</p>
            <p>All the best,<br>[Your Name]</p>
            """,
            """
            <p>Hi,</p>
            <p>I hope this email finds you well. I wanted to share some positive feedback we received on the recent changes. The client was particularly impressed with the attention to detail.</p>
            <p>Great job to everyone involved!</p>
            <p>Cheers,<br>[Your Name]</p>
            """
        ]
        
        # For replies, create a response to the original email
        if is_reply and reply_to_subject and reply_to_body:
            subject = f"Re: {reply_to_subject}"
            
            reply_bodies = [
                f"""
                <p>Thanks for reaching out!</p>
                <p>I appreciate you sharing this information. It's definitely valuable for our ongoing discussions.</p>
                <p>Let's keep in touch on this topic.</p>
                <p>Best regards,<br>[Your Name]</p>
                """,
                f"""
                <p>Thank you for your email.</p>
                <p>This is really helpful information. I'll review it in detail and get back to you if I have any questions.</p>
                <p>Have a great day!</p>
                <p>Regards,<br>[Your Name]</p>
                """,
                f"""
                <p>I appreciate you sending this over!</p>
                <p>The information looks good, and I think we're aligned on the next steps. Let me know if you need anything else from my end.</p>
                <p>Thanks again,<br>[Your Name]</p>
                """
            ]
            
            body_html = random.choice(reply_bodies)
            
            # Extract plain text from HTML
            body_text = re.sub('<.*?>', '', body_html)
            
            return {
                "subject": subject,
                "body_html": body_html,
                "body_text": body_text
            }
        else:
            # For new emails, pick a random subject and body
            subject = random.choice(subjects)
            body_html = random.choice(bodies)
            
            # Extract plain text from HTML
            body_text = re.sub('<.*?>', '', body_html)
            
            return {
                "subject": subject,
                "body_html": body_html,
                "body_text": body_text
            }
    
    @staticmethod
    async def update_daily_stats(db: Session, email_account_id: int) -> WarmupStat:
        """Update daily statistics for an email account"""
        # Get or create today's stats
        today = datetime.utcnow().date()
        stat = db.query(WarmupStat).filter(
            WarmupStat.email_account_id == email_account_id,
            WarmupStat.date == today
        ).first()
        
        if not stat:
            stat = WarmupStat(
                email_account_id=email_account_id,
                date=today
            )
            db.add(stat)
        
        # Get emails sent today
        emails_sent = db.query(WarmupEmail).filter(
            WarmupEmail.sender_id == email_account_id,
            WarmupEmail.status.in_(["sent", "delivered", "opened", "replied"]),
            WarmupEmail.sent_at >= datetime.combine(today, datetime.min.time()),
            WarmupEmail.sent_at <= datetime.combine(today, datetime.max.time())
        ).count()
        
        # Get emails received today
        emails_received = db.query(WarmupEmail).filter(
            WarmupEmail.recipient_id == email_account_id,
            WarmupEmail.status.in_(["delivered", "opened", "replied"]),
            WarmupEmail.delivered_at >= datetime.combine(today, datetime.min.time()),
            WarmupEmail.delivered_at <= datetime.combine(today, datetime.max.time())
        ).count()
        
        # Get emails opened today
        emails_opened = db.query(WarmupEmail).filter(
            WarmupEmail.recipient_id == email_account_id,
            WarmupEmail.status.in_(["opened", "replied"]),
            WarmupEmail.opened_at >= datetime.combine(today, datetime.min.time()),
            WarmupEmail.opened_at <= datetime.combine(today, datetime.max.time())
        ).count()
        
        # Get emails replied today
        emails_replied = db.query(WarmupEmail).filter(
            WarmupEmail.recipient_id == email_account_id,
            WarmupEmail.status == "replied",
            WarmupEmail.replied_at >= datetime.combine(today, datetime.min.time()),
            WarmupEmail.replied_at <= datetime.combine(today, datetime.max.time())
        ).count()
        
        # Get emails in spam today
        emails_in_spam = db.query(WarmupEmail).filter(
            WarmupEmail.recipient_id == email_account_id,
            WarmupEmail.in_spam == True,
            WarmupEmail.delivered_at >= datetime.combine(today, datetime.min.time()),
            WarmupEmail.delivered_at <= datetime.combine(today, datetime.max.time())
        ).count()
        
        # Calculate rates
        open_rate = (emails_opened / emails_received * 100) if emails_received > 0 else 0
        reply_rate = (emails_replied / emails_received * 100) if emails_received > 0 else 0
        spam_rate = (emails_in_spam / emails_received * 100) if emails_received > 0 else 0
        
        # Calculate deliverability score (higher is better)
        deliverability_score = 100 - spam_rate
        
        # Update stat
        stat.emails_sent = emails_sent
        stat.emails_received = emails_received
        stat.emails_opened = emails_opened
        stat.emails_replied = emails_replied
        stat.emails_in_spam = emails_in_spam
        stat.open_rate = open_rate
        stat.reply_rate = reply_rate
        stat.spam_rate = spam_rate
        stat.deliverability_score = deliverability_score
        
        db.commit()
        db.refresh(stat)
        
        return stat 