from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import re

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    company: Optional[str] = Field(None, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def password_strength(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    company: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None

class UserInDB(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class User(UserInDB):
    pass

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None

class EmailAccountBase(BaseModel):
    email_address: EmailStr
    display_name: Optional[str] = Field(None, max_length=100)
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    imap_host: str
    imap_port: int
    imap_username: str
    imap_password: str
    
    @validator('smtp_port', 'imap_port')
    def validate_port(cls, v):
        if v <= 0 or v > 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v

class EmailAccountCreate(EmailAccountBase):
    pass

class EmailAccountUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_username: Optional[str] = None
    imap_password: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('smtp_port', 'imap_port')
    def validate_port(cls, v):
        if v is not None and (v <= 0 or v > 65535):
            raise ValueError('Port must be between 1 and 65535')
        return v

class EmailAccountInDB(EmailAccountBase):
    id: int
    user_id: int
    domain: str
    is_active: bool
    is_verified: bool
    verification_status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class EmailAccount(BaseModel):
    id: int
    email_address: str
    display_name: Optional[str] = None
    domain: str
    is_active: bool
    is_verified: bool
    verification_status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class WarmupConfigBase(BaseModel):
    is_active: bool = True
    max_emails_per_day: int = Field(40, ge=1, le=100)
    daily_increase: int = Field(2, ge=1, le=10)
    current_daily_limit: int = Field(2, ge=1, le=100)
    min_delay_seconds: int = Field(60, ge=30, le=3600)
    max_delay_seconds: int = Field(300, ge=60, le=7200)
    target_open_rate: float = Field(80.0, ge=0.0, le=100.0)
    target_reply_rate: float = Field(40.0, ge=0.0, le=100.0)
    warmup_days: int = Field(28, ge=7, le=90)
    weekdays_only: bool = False
    randomize_volume: bool = True
    read_delay_seconds: int = Field(120, ge=30, le=3600)

class WarmupConfigCreate(WarmupConfigBase):
    email_account_id: int

class WarmupConfigUpdate(BaseModel):
    is_active: Optional[bool] = None
    max_emails_per_day: Optional[int] = Field(None, ge=1, le=100)
    daily_increase: Optional[int] = Field(None, ge=1, le=10)
    current_daily_limit: Optional[int] = Field(None, ge=1, le=100)
    min_delay_seconds: Optional[int] = Field(None, ge=30, le=3600)
    max_delay_seconds: Optional[int] = Field(None, ge=60, le=7200)
    target_open_rate: Optional[float] = Field(None, ge=0.0, le=100.0)
    target_reply_rate: Optional[float] = Field(None, ge=0.0, le=100.0)
    warmup_days: Optional[int] = Field(None, ge=7, le=90)
    weekdays_only: Optional[bool] = None
    randomize_volume: Optional[bool] = None
    read_delay_seconds: Optional[int] = Field(None, ge=30, le=3600)

class WarmupConfigInDB(WarmupConfigBase):
    id: int
    user_id: int
    email_account_id: int
    start_date: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class WarmupConfig(WarmupConfigInDB):
    pass

class WarmupStatBase(BaseModel):
    date: datetime
    emails_sent: int = 0
    emails_received: int = 0
    emails_opened: int = 0
    emails_replied: int = 0
    emails_in_spam: int = 0
    open_rate: float = 0.0
    reply_rate: float = 0.0
    spam_rate: float = 0.0
    deliverability_score: float = 0.0

class WarmupStatCreate(WarmupStatBase):
    email_account_id: int

class WarmupStatInDB(WarmupStatBase):
    id: int
    email_account_id: int
    
    class Config:
        orm_mode = True

class WarmupStat(WarmupStatInDB):
    pass

class WarmupEmailBase(BaseModel):
    message_id: str
    sender_id: int
    recipient_id: int
    subject: str
    body: str
    status: str
    is_reply: bool = False
    in_spam: bool = False

class WarmupEmailCreate(WarmupEmailBase):
    pass

class WarmupEmailUpdate(BaseModel):
    status: Optional[str] = None
    is_reply: Optional[bool] = None
    in_spam: Optional[bool] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    error_message: Optional[str] = None

class WarmupEmailInDB(WarmupEmailBase):
    id: int
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    
    class Config:
        orm_mode = True

class WarmupEmail(WarmupEmailInDB):
    pass

class DNSRecordBase(BaseModel):
    record_type: str
    record_name: str
    record_value: str
    is_verified: bool = False

class DNSRecordCreate(DNSRecordBase):
    email_account_id: int

class DNSRecordUpdate(BaseModel):
    record_value: Optional[str] = None
    is_verified: Optional[bool] = None
    last_checked: Optional[datetime] = None

class DNSRecordInDB(DNSRecordBase):
    id: int
    email_account_id: int
    last_checked: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class DNSRecord(DNSRecordInDB):
    pass

class DomainVerificationRequest(BaseModel):
    email_account_id: int

class DomainVerificationResponse(BaseModel):
    success: bool
    message: str
    records: Optional[List[DNSRecord]] = None

class WarmupStatusResponse(BaseModel):
    email_account_id: int
    is_active: bool
    current_daily_limit: int
    days_in_warmup: int
    total_warmup_days: int
    warmup_progress: float  # Percentage
    deliverability_score: float
    open_rate: float
    reply_rate: float
    spam_rate: float
    total_emails_sent: int
    total_emails_received: int

class DashboardStats(BaseModel):
    total_accounts: int
    active_accounts: int
    verified_accounts: int
    total_emails_sent: int
    total_emails_opened: int
    total_emails_replied: int
    average_deliverability: float
    account_stats: List[WarmupStatusResponse] 