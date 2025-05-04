from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.auth import get_current_active_user
from app.db.database import get_db
from app.models.models import User, EmailAccount, WarmupConfig
from app.schemas.schemas import EmailAccount as EmailAccountSchema, EmailAccountCreate, EmailAccountUpdate
from app.services.email_service import EmailService
from app.services.dns_service import DNSService

router = APIRouter()

@router.get("/", response_model=List[EmailAccountSchema])
async def read_email_accounts(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all email accounts for the current user
    """
    email_accounts = db.query(EmailAccount).filter(
        EmailAccount.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return email_accounts

@router.post("/", response_model=EmailAccountSchema)
async def create_email_account(
    email_account: EmailAccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new email account
    """
    # Check if email account already exists
    if db.query(EmailAccount).filter(EmailAccount.email_address == email_account.email_address).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email account already registered"
        )
    
    # Extract domain from email address
    domain = email_account.email_address.split('@')[1]
    
    # Create email account
    db_email_account = EmailAccount(
        user_id=current_user.id,
        email_address=email_account.email_address,
        display_name=email_account.display_name,
        smtp_host=email_account.smtp_host,
        smtp_port=email_account.smtp_port,
        smtp_username=email_account.smtp_username,
        smtp_password=email_account.smtp_password,
        imap_host=email_account.imap_host,
        imap_port=email_account.imap_port,
        imap_username=email_account.imap_username,
        imap_password=email_account.imap_password,
        domain=domain
    )
    
    db.add(db_email_account)
    db.commit()
    db.refresh(db_email_account)
    
    # Verify SMTP and IMAP connections
    smtp_verified = await EmailService.verify_smtp_connection(db_email_account)
    imap_verified = await EmailService.verify_imap_connection(db_email_account)
    
    # Update verification status
    if smtp_verified and imap_verified:
        db_email_account.verification_status = "verified"
    else:
        db_email_account.verification_status = "failed"
        error_details = []
        if not smtp_verified:
            error_details.append("SMTP connection failed")
        if not imap_verified:
            error_details.append("IMAP connection failed")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email account verification failed: {', '.join(error_details)}"
        )
    
    # Generate DNS records for the domain
    dns_result = await DNSService.verify_dns_records(db, db_email_account.id)
    
    # Create default warmup configuration
    warmup_config = WarmupConfig(
        user_id=current_user.id,
        email_account_id=db_email_account.id
    )
    db.add(warmup_config)
    
    db.commit()
    db.refresh(db_email_account)
    
    return db_email_account

@router.get("/{email_account_id}", response_model=EmailAccountSchema)
async def read_email_account(
    email_account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get email account by ID
    """
    email_account = db.query(EmailAccount).filter(
        EmailAccount.id == email_account_id,
        EmailAccount.user_id == current_user.id
    ).first()
    
    if email_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )
    
    return email_account

@router.put("/{email_account_id}", response_model=EmailAccountSchema)
async def update_email_account(
    email_account_id: int,
    email_account_update: EmailAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update email account by ID
    """
    db_email_account = db.query(EmailAccount).filter(
        EmailAccount.id == email_account_id,
        EmailAccount.user_id == current_user.id
    ).first()
    
    if db_email_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )
    
    # Update fields
    if email_account_update.display_name is not None:
        db_email_account.display_name = email_account_update.display_name
    
    if email_account_update.smtp_host is not None:
        db_email_account.smtp_host = email_account_update.smtp_host
    
    if email_account_update.smtp_port is not None:
        db_email_account.smtp_port = email_account_update.smtp_port
    
    if email_account_update.smtp_username is not None:
        db_email_account.smtp_username = email_account_update.smtp_username
    
    if email_account_update.smtp_password is not None:
        db_email_account.smtp_password = email_account_update.smtp_password
    
    if email_account_update.imap_host is not None:
        db_email_account.imap_host = email_account_update.imap_host
    
    if email_account_update.imap_port is not None:
        db_email_account.imap_port = email_account_update.imap_port
    
    if email_account_update.imap_username is not None:
        db_email_account.imap_username = email_account_update.imap_username
    
    if email_account_update.imap_password is not None:
        db_email_account.imap_password = email_account_update.imap_password
    
    if email_account_update.is_active is not None:
        db_email_account.is_active = email_account_update.is_active
    
    # Commit changes
    db.commit()
    
    # Verify SMTP and IMAP connections if credentials changed
    connection_updated = any([
        email_account_update.smtp_host is not None,
        email_account_update.smtp_port is not None,
        email_account_update.smtp_username is not None,
        email_account_update.smtp_password is not None,
        email_account_update.imap_host is not None,
        email_account_update.imap_port is not None,
        email_account_update.imap_username is not None,
        email_account_update.imap_password is not None
    ])
    
    if connection_updated:
        smtp_verified = await EmailService.verify_smtp_connection(db_email_account)
        imap_verified = await EmailService.verify_imap_connection(db_email_account)
        
        # Update verification status
        if smtp_verified and imap_verified:
            db_email_account.verification_status = "verified"
        else:
            db_email_account.verification_status = "failed"
            error_details = []
            if not smtp_verified:
                error_details.append("SMTP connection failed")
            if not imap_verified:
                error_details.append("IMAP connection failed")
            
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email account verification failed: {', '.join(error_details)}"
            )
    
    db.refresh(db_email_account)
    
    return db_email_account

@router.delete("/{email_account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_account(
    email_account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete email account by ID
    """
    email_account = db.query(EmailAccount).filter(
        EmailAccount.id == email_account_id,
        EmailAccount.user_id == current_user.id
    ).first()
    
    if email_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )
    
    db.delete(email_account)
    db.commit()
    
    return {"status": "success"}

@router.post("/{email_account_id}/verify", status_code=status.HTTP_200_OK)
async def verify_email_account(
    email_account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Verify email account credentials and DNS records
    """
    email_account = db.query(EmailAccount).filter(
        EmailAccount.id == email_account_id,
        EmailAccount.user_id == current_user.id
    ).first()
    
    if email_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )
    
    # Verify SMTP and IMAP connections
    smtp_verified = await EmailService.verify_smtp_connection(email_account)
    imap_verified = await EmailService.verify_imap_connection(email_account)
    
    # Verify DNS records
    dns_result = await DNSService.verify_dns_records(db, email_account_id)
    
    # Update verification status
    if smtp_verified and imap_verified and dns_result.get("verified", False):
        email_account.is_verified = True
        email_account.verification_status = "verified"
    else:
        email_account.is_verified = False
        email_account.verification_status = "failed"
        error_details = []
        if not smtp_verified:
            error_details.append("SMTP connection failed")
        if not imap_verified:
            error_details.append("IMAP connection failed")
        if not dns_result.get("verified", False):
            error_details.append("DNS records verification failed")
        
        db.commit()
        
        return {
            "status": "failed",
            "details": error_details,
            "dns_records": dns_result.get("records", [])
        }
    
    db.commit()
    
    return {
        "status": "success",
        "smtp_verified": smtp_verified,
        "imap_verified": imap_verified,
        "dns_verified": dns_result.get("verified", False),
        "dns_records": dns_result.get("records", [])
    } 