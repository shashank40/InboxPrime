import asyncio
import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.models import EmailAccount, WarmupConfig, WarmupEmail, WarmupStat
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

class WarmupService:
    """Service for email warmup operations"""
    
    @staticmethod
    async def get_daily_target(config: WarmupConfig, days_in_warmup: int) -> int:
        """
        Calculate the daily target number of emails based on warmup configuration
        and the number of days the account has been in warmup
        """
        # Start with the current daily limit
        target = min(config.current_daily_limit, config.max_emails_per_day)
        
        # If randomize_volume is enabled, vary the target by ±20%
        if config.randomize_volume:
            variance = round(target * 0.2)  # 20% variance
            if variance > 0:
                target = random.randint(max(1, target - variance), target + variance)
        
        return min(target, config.max_emails_per_day)
    
    @staticmethod
    async def update_daily_limit(db: Session, config: WarmupConfig, days_in_warmup: int) -> WarmupConfig:
        """
        Update the daily email limit based on warmup progression
        """
        if days_in_warmup > 0 and days_in_warmup % 1 == 0:  # Every day
            # Increase the daily limit
            new_limit = min(
                config.current_daily_limit + config.daily_increase,
                config.max_emails_per_day
            )
            
            # Update the config
            config.current_daily_limit = new_limit
            db.commit()
            db.refresh(config)
        
        return config
    
    @staticmethod
    async def get_recipient_accounts(
        db: Session, 
        sender_account_id: int, 
        count: int
    ) -> List[EmailAccount]:
        """
        Get a list of recipient accounts for warmup emails
        We want to get accounts that:
        1. Are not the sender
        2. Are active
        3. Are verified
        4. Preferably have not received warmup emails from this sender recently
        """
        # Get accounts that have not received emails from the sender recently
        subquery = db.query(WarmupEmail.recipient_id).filter(
            WarmupEmail.sender_id == sender_account_id,
            WarmupEmail.sent_at >= datetime.utcnow() - timedelta(days=7)
        ).subquery()
        
        # Get fresh recipients (not contacted in the last week)
        fresh_recipients = db.query(EmailAccount).filter(
            EmailAccount.id != sender_account_id,
            EmailAccount.is_active == True,
            EmailAccount.is_verified == True,
            ~EmailAccount.id.in_(subquery)
        ).order_by(func.random()).limit(count).all()
        
        # If we don't have enough fresh recipients, get some random ones
        if len(fresh_recipients) < count:
            remaining_count = count - len(fresh_recipients)
            random_recipients = db.query(EmailAccount).filter(
                EmailAccount.id != sender_account_id,
                EmailAccount.is_active == True,
                EmailAccount.is_verified == True,
                ~EmailAccount.id.in_([r.id for r in fresh_recipients])
            ).order_by(func.random()).limit(remaining_count).all()
            
            fresh_recipients.extend(random_recipients)
        
        return fresh_recipients
    
    @staticmethod
    async def send_warmup_emails(db: Session, email_account_id: int) -> Dict[str, Any]:
        """
        Send warmup emails for a specific account
        """
        result = {
            "success": True,
            "emails_sent": 0,
            "errors": []
        }
        
        try:
            # Get the email account
            email_account = db.query(EmailAccount).filter(
                EmailAccount.id == email_account_id,
                EmailAccount.is_active == True,
                EmailAccount.is_verified == True
            ).first()
            
            if not email_account:
                result["success"] = False
                result["errors"].append("Email account not found or not active/verified")
                return result
            
            # Get the warmup config
            config = db.query(WarmupConfig).filter(
                WarmupConfig.email_account_id == email_account_id,
                WarmupConfig.is_active == True
            ).first()
            
            if not config:
                result["success"] = False
                result["errors"].append("Warmup configuration not found or not active")
                return result
            
            # Check if we should send emails today (weekdays only option)
            if config.weekdays_only and datetime.utcnow().weekday() >= 5:  # 5=Saturday, 6=Sunday
                result["success"] = True
                result["emails_sent"] = 0
                result["skipped"] = "Weekend day with weekdays_only enabled"
                return result
            
            # Calculate days in warmup
            days_in_warmup = (datetime.utcnow().date() - config.start_date.date()).days
            
            # Update the daily limit based on warmup progression
            config = await WarmupService.update_daily_limit(db, config, days_in_warmup)
            
            # Get daily target
            daily_target = await WarmupService.get_daily_target(config, days_in_warmup)
            
            # Check how many emails were already sent today
            emails_sent_today = db.query(WarmupEmail).filter(
                WarmupEmail.sender_id == email_account_id,
                WarmupEmail.sent_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
                WarmupEmail.sent_at <= datetime.utcnow()
            ).count()
            
            # Calculate how many more emails to send
            emails_to_send = max(0, daily_target - emails_sent_today)
            
            if emails_to_send <= 0:
                result["success"] = True
                result["emails_sent"] = 0
                result["skipped"] = f"Daily target reached ({daily_target})"
                return result
            
            # Get recipient accounts
            recipients = await WarmupService.get_recipient_accounts(db, email_account_id, emails_to_send)
            
            if not recipients:
                result["success"] = False
                result["errors"].append("No recipient accounts available")
                return result
            
            # Send emails to recipients
            for recipient in recipients:
                try:
                    # Generate unique ID for this warmup email
                    warmup_id = str(uuid.uuid4())[:8]
                    
                    # Generate email content
                    email_content = await EmailService.generate_warmup_email(warmup_id)
                    
                    # Send the email
                    success, message, message_id = await EmailService.send_email(
                        sender=email_account,
                        recipient_email=recipient.email_address,
                        subject=email_content["subject"],
                        body_html=email_content["body_html"],
                        body_text=email_content["body_text"]
                    )
                    
                    if success and message_id:
                        # Record the sent email
                        warmup_email = WarmupEmail(
                            message_id=message_id,
                            sender_id=email_account_id,
                            recipient_id=recipient.id,
                            subject=email_content["subject"],
                            body=email_content["body_html"],
                            status="sent",
                            sent_at=datetime.utcnow()
                        )
                        db.add(warmup_email)
                        db.commit()
                        
                        result["emails_sent"] += 1
                        
                        # Add random delay between emails
                        delay_seconds = random.randint(config.min_delay_seconds, config.max_delay_seconds)
                        await asyncio.sleep(delay_seconds)
                    else:
                        result["errors"].append(f"Failed to send to {recipient.email_address}: {message}")
                except Exception as e:
                    result["errors"].append(f"Error sending to {recipient.email_address}: {str(e)}")
            
            # Update daily stats
            await EmailService.update_daily_stats(db, email_account_id)
            
            return result
        except Exception as e:
            logger.error(f"Failed to send warmup emails: {str(e)}")
            result["success"] = False
            result["errors"].append(f"Failed to send warmup emails: {str(e)}")
            return result
    
    @staticmethod
    async def process_incoming_warmup_emails(db: Session, email_account_id: int) -> Dict[str, Any]:
        """
        Process incoming warmup emails:
        1. Check inbox for warmup emails
        2. Mark them as read
        3. Reply to them if configured
        4. Update statistics
        """
        result = {
            "success": True,
            "emails_processed": 0,
            "emails_in_spam": 0,
            "errors": []
        }
        
        try:
            # Get the email account
            email_account = db.query(EmailAccount).filter(
                EmailAccount.id == email_account_id,
                EmailAccount.is_active == True,
                EmailAccount.is_verified == True
            ).first()
            
            if not email_account:
                result["success"] = False
                result["errors"].append("Email account not found or not active/verified")
                return result
            
            # Get the warmup config
            config = db.query(WarmupConfig).filter(
                WarmupConfig.email_account_id == email_account_id,
                WarmupConfig.is_active == True
            ).first()
            
            if not config:
                result["success"] = False
                result["errors"].append("Warmup configuration not found or not active")
                return result
            
            # Check inbox for warmup emails
            inbox_stats = await EmailService.check_inbox(email_account, look_for_warmup_emails=True, process_replies=True)
            
            result["emails_processed"] = len(inbox_stats["processed"])
            result["emails_in_spam"] = inbox_stats["in_spam"]
            
            # Process each warmup email
            for processed_email in inbox_stats["processed"]:
                try:
                    # Find the warmup email in the database
                    message_id = processed_email["message_id"]
                    warmup_email = db.query(WarmupEmail).filter(
                        WarmupEmail.message_id == message_id,
                        WarmupEmail.recipient_id == email_account_id
                    ).first()
                    
                    if warmup_email:
                        # Update the email status
                        warmup_email.status = "opened"
                        warmup_email.opened_at = datetime.utcnow()
                        
                        # Decide if we should reply (based on target reply rate)
                        should_reply = random.random() * 100 <= config.target_reply_rate
                        
                        if should_reply and not warmup_email.is_reply:
                            # Get the sender account
                            sender_account = db.query(EmailAccount).filter(
                                EmailAccount.id == warmup_email.sender_id
                            ).first()
                            
                            if sender_account:
                                # Generate reply content
                                reply_content = await EmailService.generate_warmup_email(
                                    warmup_id=str(uuid.uuid4())[:8],
                                    is_reply=True,
                                    reply_to_subject=warmup_email.subject,
                                    reply_to_body=warmup_email.body
                                )
                                
                                # Wait a random delay to simulate reading time
                                read_delay = random.randint(30, config.read_delay_seconds)
                                await asyncio.sleep(read_delay)
                                
                                # Send the reply
                                success, message, reply_message_id = await EmailService.send_email(
                                    sender=email_account,
                                    recipient_email=sender_account.email_address,
                                    subject=reply_content["subject"],
                                    body_html=reply_content["body_html"],
                                    body_text=reply_content["body_text"]
                                )
                                
                                if success and reply_message_id:
                                    # Update the original email status
                                    warmup_email.status = "replied"
                                    warmup_email.replied_at = datetime.utcnow()
                                    
                                    # Record the reply email
                                    reply_email = WarmupEmail(
                                        message_id=reply_message_id,
                                        sender_id=email_account_id,
                                        recipient_id=warmup_email.sender_id,
                                        subject=reply_content["subject"],
                                        body=reply_content["body_html"],
                                        status="sent",
                                        is_reply=True,
                                        sent_at=datetime.utcnow()
                                    )
                                    db.add(reply_email)
                    else:
                        # Record the new received email
                        warmup_id_match = re.search(r'WARMUP-([a-f0-9]+):', processed_email["subject"])
                        if warmup_id_match:
                            new_warmup_email = WarmupEmail(
                                message_id=processed_email["message_id"],
                                sender_id=None,  # We don't know the sender_id in our system
                                recipient_id=email_account_id,
                                subject=processed_email["subject"],
                                body="",  # We don't have the body here
                                status="opened",
                                opened_at=datetime.utcnow(),
                                delivered_at=datetime.utcnow(),
                                in_spam=False
                            )
                            db.add(new_warmup_email)
                            
                except Exception as e:
                    result["errors"].append(f"Error processing email {processed_email['message_id']}: {str(e)}")
            
            # Check for warmup emails in spam
            for warmup_email in db.query(WarmupEmail).filter(
                WarmupEmail.recipient_id == email_account_id,
                WarmupEmail.status == "delivered",
                WarmupEmail.in_spam == True
            ).all():
                # Update the email status
                warmup_email.status = "opened"
                warmup_email.opened_at = datetime.utcnow()
            
            # Commit all changes
            db.commit()
            
            # Update daily stats
            await EmailService.update_daily_stats(db, email_account_id)
            
            return result
        except Exception as e:
            logger.error(f"Failed to process incoming warmup emails: {str(e)}")
            result["success"] = False
            result["errors"].append(f"Failed to process incoming warmup emails: {str(e)}")
            return result

    @staticmethod
    async def run_warmup_cycle(db: Session) -> Dict[str, Any]:
        """
        Run a complete warmup cycle for all active accounts:
        1. Process incoming warmup emails
        2. Send new warmup emails
        """
        result = {
            "success": True,
            "accounts_processed": 0,
            "total_emails_sent": 0,
            "account_results": [],
            "errors": []
        }
        
        try:
            # Get all active email accounts with active warmup configs
            accounts = db.query(EmailAccount).join(
                WarmupConfig,
                EmailAccount.id == WarmupConfig.email_account_id
            ).filter(
                EmailAccount.is_active == True,
                EmailAccount.is_verified == True,
                WarmupConfig.is_active == True
            ).all()
            
            for account in accounts:
                try:
                    # Process incoming emails first
                    process_result = await WarmupService.process_incoming_warmup_emails(db, account.id)
                    
                    # Then send new warmup emails
                    send_result = await WarmupService.send_warmup_emails(db, account.id)
                    
                    account_result = {
                        "email_account_id": account.id,
                        "email_address": account.email_address,
                        "emails_processed": process_result.get("emails_processed", 0),
                        "emails_in_spam": process_result.get("emails_in_spam", 0),
                        "emails_sent": send_result.get("emails_sent", 0),
                        "errors": process_result.get("errors", []) + send_result.get("errors", [])
                    }
                    
                    result["accounts_processed"] += 1
                    result["total_emails_sent"] += send_result.get("emails_sent", 0)
                    result["account_results"].append(account_result)
                    
                except Exception as e:
                    error_msg = f"Error processing account {account.email_address}: {str(e)}"
                    result["errors"].append(error_msg)
                    logger.error(error_msg)
            
            return result
        except Exception as e:
            logger.error(f"Failed to run warmup cycle: {str(e)}")
            result["success"] = False
            result["errors"].append(f"Failed to run warmup cycle: {str(e)}")
            return result

    @staticmethod
    async def get_warmup_status(db: Session, email_account_id: int) -> Dict[str, Any]:
        """Get the current warmup status for an email account"""
        try:
            # Get the email account
            email_account = db.query(EmailAccount).filter(
                EmailAccount.id == email_account_id
            ).first()
            
            if not email_account:
                return {
                    "success": False,
                    "error": "Email account not found"
                }
            
            # Get the warmup config
            config = db.query(WarmupConfig).filter(
                WarmupConfig.email_account_id == email_account_id
            ).first()
            
            if not config:
                return {
                    "success": False,
                    "error": "Warmup configuration not found"
                }
            
            # Calculate days in warmup
            days_in_warmup = (datetime.utcnow().date() - config.start_date.date()).days
            warmup_progress = min(100, (days_in_warmup / config.warmup_days) * 100)
            
            # Get latest stats
            latest_stat = db.query(WarmupStat).filter(
                WarmupStat.email_account_id == email_account_id
            ).order_by(desc(WarmupStat.date)).first()
            
            # Get total emails sent and received
            total_sent = db.query(func.count(WarmupEmail.id)).filter(
                WarmupEmail.sender_id == email_account_id
            ).scalar() or 0
            
            total_received = db.query(func.count(WarmupEmail.id)).filter(
                WarmupEmail.recipient_id == email_account_id
            ).scalar() or 0
            
            return {
                "success": True,
                "email_account_id": email_account_id,
                "is_active": config.is_active,
                "current_daily_limit": config.current_daily_limit,
                "days_in_warmup": days_in_warmup,
                "total_warmup_days": config.warmup_days,
                "warmup_progress": warmup_progress,
                "deliverability_score": latest_stat.deliverability_score if latest_stat else 100,
                "open_rate": latest_stat.open_rate if latest_stat else 0,
                "reply_rate": latest_stat.reply_rate if latest_stat else 0,
                "spam_rate": latest_stat.spam_rate if latest_stat else 0,
                "total_emails_sent": total_sent,
                "total_emails_received": total_received
            }
        except Exception as e:
            logger.error(f"Failed to get warmup status: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get warmup status: {str(e)}"
            } 