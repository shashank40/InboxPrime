from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.core.auth import get_current_active_user, get_current_admin_user
from app.db.database import get_db
from app.models.models import User, EmailAccount, WarmupConfig, WarmupStat
from app.schemas.schemas import WarmupConfig as WarmupConfigSchema, WarmupConfigCreate, WarmupConfigUpdate, WarmupStatusResponse
from app.services.warmup_service import WarmupService

router = APIRouter()

@router.get("/configs", response_model=List[WarmupConfigSchema])
async def read_warmup_configs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all warmup configurations for the current user
    """
    configs = db.query(WarmupConfig).filter(
        WarmupConfig.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return configs

@router.post("/configs", response_model=WarmupConfigSchema)
async def create_warmup_config(
    config: WarmupConfigCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new warmup configuration
    """
    # Check if the email account exists and belongs to the user
    email_account = db.query(EmailAccount).filter(
        EmailAccount.id == config.email_account_id,
        EmailAccount.user_id == current_user.id
    ).first()
    
    if email_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )
    
    # Check if a config already exists for this email account
    existing_config = db.query(WarmupConfig).filter(
        WarmupConfig.email_account_id == config.email_account_id
    ).first()
    
    if existing_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warmup configuration already exists for this email account"
        )
    
    # Create warmup configuration
    db_config = WarmupConfig(
        user_id=current_user.id,
        email_account_id=config.email_account_id,
        is_active=config.is_active,
        max_emails_per_day=config.max_emails_per_day,
        daily_increase=config.daily_increase,
        current_daily_limit=config.current_daily_limit,
        min_delay_seconds=config.min_delay_seconds,
        max_delay_seconds=config.max_delay_seconds,
        target_open_rate=config.target_open_rate,
        target_reply_rate=config.target_reply_rate,
        warmup_days=config.warmup_days,
        weekdays_only=config.weekdays_only,
        randomize_volume=config.randomize_volume,
        read_delay_seconds=config.read_delay_seconds
    )
    
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    return db_config

@router.get("/configs/{email_account_id}", response_model=WarmupConfigSchema)
async def read_warmup_config(
    email_account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get warmup configuration for an email account
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
    
    # Get the warmup configuration
    config = db.query(WarmupConfig).filter(
        WarmupConfig.email_account_id == email_account_id
    ).first()
    
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warmup configuration not found"
        )
    
    return config

@router.put("/configs/{email_account_id}", response_model=WarmupConfigSchema)
async def update_warmup_config(
    email_account_id: int,
    config_update: WarmupConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update warmup configuration for an email account
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
    
    # Get the warmup configuration
    config = db.query(WarmupConfig).filter(
        WarmupConfig.email_account_id == email_account_id
    ).first()
    
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warmup configuration not found"
        )
    
    # Update fields
    if config_update.is_active is not None:
        config.is_active = config_update.is_active
    
    if config_update.max_emails_per_day is not None:
        config.max_emails_per_day = config_update.max_emails_per_day
    
    if config_update.daily_increase is not None:
        config.daily_increase = config_update.daily_increase
    
    if config_update.current_daily_limit is not None:
        config.current_daily_limit = config_update.current_daily_limit
    
    if config_update.min_delay_seconds is not None:
        config.min_delay_seconds = config_update.min_delay_seconds
    
    if config_update.max_delay_seconds is not None:
        config.max_delay_seconds = config_update.max_delay_seconds
    
    if config_update.target_open_rate is not None:
        config.target_open_rate = config_update.target_open_rate
    
    if config_update.target_reply_rate is not None:
        config.target_reply_rate = config_update.target_reply_rate
    
    if config_update.warmup_days is not None:
        config.warmup_days = config_update.warmup_days
    
    if config_update.weekdays_only is not None:
        config.weekdays_only = config_update.weekdays_only
    
    if config_update.randomize_volume is not None:
        config.randomize_volume = config_update.randomize_volume
    
    if config_update.read_delay_seconds is not None:
        config.read_delay_seconds = config_update.read_delay_seconds
    
    # Commit changes
    db.commit()
    db.refresh(config)
    
    return config

@router.post("/run/{email_account_id}", status_code=status.HTTP_202_ACCEPTED)
async def run_warmup_for_account(
    email_account_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Manually run warmup for a specific email account
    """
    # Check if the email account exists and belongs to the user
    email_account = db.query(EmailAccount).filter(
        EmailAccount.id == email_account_id,
        EmailAccount.user_id == current_user.id,
        EmailAccount.is_active == True,
        EmailAccount.is_verified == True
    ).first()
    
    if email_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found or not active/verified"
        )
    
    # Check if warmup is configured
    config = db.query(WarmupConfig).filter(
        WarmupConfig.email_account_id == email_account_id,
        WarmupConfig.is_active == True
    ).first()
    
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warmup not configured or not active for this account"
        )
    
    # Add warmup task to background tasks
    background_tasks.add_task(WarmupService.send_warmup_emails, db, email_account_id)
    
    return {"status": "Warmup initiated in background"}

@router.post("/run", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(get_current_admin_user)])
async def run_warmup_cycle(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Run warmup cycle for all active and verified accounts (admin only)
    """
    # Add warmup cycle task to background tasks
    background_tasks.add_task(WarmupService.run_warmup_cycle, db)
    
    return {"status": "Warmup cycle initiated in background"}

@router.get("/status/{email_account_id}", response_model=WarmupStatusResponse)
async def get_warmup_status(
    email_account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get warmup status for an email account
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
    
    # Get warmup status
    status = await WarmupService.get_warmup_status(db, email_account_id)
    
    if not status.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=status.get("error", "Failed to get warmup status")
        )
    
    return status

@router.post("/toggle/{email_account_id}", response_model=WarmupConfigSchema)
async def toggle_warmup(
    email_account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Toggle warmup for an email account (enable/disable)
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
    
    # Get the warmup configuration
    config = db.query(WarmupConfig).filter(
        WarmupConfig.email_account_id == email_account_id
    ).first()
    
    if config is None:
        # Create default config if it doesn't exist
        config = WarmupConfig(
            user_id=current_user.id,
            email_account_id=email_account_id,
            is_active=True
        )
        db.add(config)
    else:
        # Toggle is_active
        config.is_active = not config.is_active
    
    db.commit()
    db.refresh(config)
    
    return config 