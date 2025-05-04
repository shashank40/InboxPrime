from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any
from app.core.auth import get_current_active_user
from app.db.database import get_db
from app.models.models import User, EmailAccount, WarmupConfig, WarmupStat, WarmupEmail
from app.schemas.schemas import DashboardStats, WarmupStatusResponse
from app.services.warmup_service import WarmupService
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for the current user
    """
    # Get email accounts
    accounts = db.query(EmailAccount).filter(
        EmailAccount.user_id == current_user.id
    ).all()
    
    # If no accounts, return empty stats
    if not accounts:
        return DashboardStats(
            total_accounts=0,
            active_accounts=0,
            verified_accounts=0,
            total_emails_sent=0,
            total_emails_opened=0,
            total_emails_replied=0,
            average_deliverability=0.0,
            account_stats=[]
        )
    
    # Count accounts
    total_accounts = len(accounts)
    active_accounts = len([a for a in accounts if a.is_active])
    verified_accounts = len([a for a in accounts if a.is_verified])
    
    # Get account IDs
    account_ids = [a.id for a in accounts]
    
    # Get email stats
    total_emails_sent = db.query(func.count(WarmupEmail.id)).filter(
        WarmupEmail.sender_id.in_(account_ids)
    ).scalar() or 0
    
    total_emails_opened = db.query(func.count(WarmupEmail.id)).filter(
        WarmupEmail.recipient_id.in_(account_ids),
        WarmupEmail.status.in_(["opened", "replied"])
    ).scalar() or 0
    
    total_emails_replied = db.query(func.count(WarmupEmail.id)).filter(
        WarmupEmail.recipient_id.in_(account_ids),
        WarmupEmail.status == "replied"
    ).scalar() or 0
    
    # Get average deliverability
    latest_stats = db.query(WarmupStat).filter(
        WarmupStat.email_account_id.in_(account_ids)
    ).order_by(desc(WarmupStat.date)).limit(len(account_ids)).all()
    
    # Calculate average deliverability
    if latest_stats:
        average_deliverability = sum(s.deliverability_score for s in latest_stats) / len(latest_stats)
    else:
        average_deliverability = 100.0  # Default if no stats
    
    # Get account stats
    account_stats = []
    for account in accounts:
        status = await WarmupService.get_warmup_status(db, account.id)
        if status.get("success", False):
            account_stats.append(WarmupStatusResponse(
                email_account_id=account.id,
                is_active=status.get("is_active", False),
                current_daily_limit=status.get("current_daily_limit", 0),
                days_in_warmup=status.get("days_in_warmup", 0),
                total_warmup_days=status.get("total_warmup_days", 0),
                warmup_progress=status.get("warmup_progress", 0.0),
                deliverability_score=status.get("deliverability_score", 0.0),
                open_rate=status.get("open_rate", 0.0),
                reply_rate=status.get("reply_rate", 0.0),
                spam_rate=status.get("spam_rate", 0.0),
                total_emails_sent=status.get("total_emails_sent", 0),
                total_emails_received=status.get("total_emails_received", 0)
            ))
    
    return DashboardStats(
        total_accounts=total_accounts,
        active_accounts=active_accounts,
        verified_accounts=verified_accounts,
        total_emails_sent=total_emails_sent,
        total_emails_opened=total_emails_opened,
        total_emails_replied=total_emails_replied,
        average_deliverability=average_deliverability,
        account_stats=account_stats
    )

@router.get("/history/{email_account_id}")
async def get_account_history(
    email_account_id: int,
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get historical data for an email account
    """
    # Check if the email account exists and belongs to the user
    email_account = db.query(EmailAccount).filter(
        EmailAccount.id == email_account_id,
        EmailAccount.user_id == current_user.id
    ).first()
    
    if email_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )
    
    # Get stats for the last N days
    start_date = datetime.utcnow().date() - timedelta(days=days)
    stats = db.query(WarmupStat).filter(
        WarmupStat.email_account_id == email_account_id,
        WarmupStat.date >= start_date
    ).order_by(WarmupStat.date).all()
    
    # Format the data
    history = []
    for stat in stats:
        history.append({
            "date": stat.date.strftime("%Y-%m-%d"),
            "emails_sent": stat.emails_sent,
            "emails_received": stat.emails_received,
            "emails_opened": stat.emails_opened,
            "emails_replied": stat.emails_replied,
            "emails_in_spam": stat.emails_in_spam,
            "open_rate": stat.open_rate,
            "reply_rate": stat.reply_rate,
            "spam_rate": stat.spam_rate,
            "deliverability_score": stat.deliverability_score
        })
    
    return {
        "email_account_id": email_account_id,
        "email_address": email_account.email_address,
        "days": days,
        "history": history
    } 