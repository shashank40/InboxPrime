from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Float, Text, JSON, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.database import Base

class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(100), nullable=True)
    company = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    email_accounts = relationship("EmailAccount", back_populates="owner", cascade="all, delete-orphan")
    warmup_configs = relationship("WarmupConfig", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.username}>"

class EmailAccount(Base):
    """Email account model"""
    __tablename__ = "email_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    email_address = Column(String(255), unique=True, index=True)
    display_name = Column(String(100), nullable=True)
    smtp_host = Column(String(255))
    smtp_port = Column(Integer)
    smtp_username = Column(String(255))
    smtp_password = Column(String(255))  # Encrypted in service layer
    imap_host = Column(String(255))
    imap_port = Column(Integer)
    imap_username = Column(String(255))
    imap_password = Column(String(255))  # Encrypted in service layer
    domain = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_status = Column(String(50), default="pending")  # pending, verified, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="email_accounts")
    warmup_stats = relationship("WarmupStat", back_populates="email_account", cascade="all, delete-orphan")
    config = relationship("WarmupConfig", back_populates="email_account", cascade="all, delete-orphan", uselist=False)
    sent_emails = relationship("WarmupEmail", back_populates="sender", foreign_keys="[WarmupEmail.sender_id]", cascade="all, delete-orphan")
    received_emails = relationship("WarmupEmail", back_populates="recipient", foreign_keys="[WarmupEmail.recipient_id]", cascade="all, delete-orphan")
    dns_records = relationship("DomainDNSRecord", back_populates="email_account", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<EmailAccount {self.email_address}>"

class WarmupConfig(Base):
    """Email warmup configuration model"""
    __tablename__ = "warmup_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    email_account_id = Column(Integer, ForeignKey("email_accounts.id"), unique=True)
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    max_emails_per_day = Column(Integer, default=40)
    daily_increase = Column(Integer, default=2)  # Increase by X emails per day
    current_daily_limit = Column(Integer, default=2)  # Start with X emails per day
    min_delay_seconds = Column(Integer, default=60)  # Min delay between emails
    max_delay_seconds = Column(Integer, default=300)  # Max delay between emails
    target_open_rate = Column(Float, default=80.0)  # Target percentage
    target_reply_rate = Column(Float, default=40.0)  # Target percentage
    warmup_days = Column(Integer, default=28)  # Initial warmup period
    weekdays_only = Column(Boolean, default=False)  # Send emails only on weekdays
    randomize_volume = Column(Boolean, default=True)  # Randomize daily volume
    read_delay_seconds = Column(Integer, default=120)  # Delay before reading emails
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="warmup_configs")
    email_account = relationship("EmailAccount", back_populates="config")
    
    def __repr__(self):
        return f"<WarmupConfig for {self.email_account_id}>"

class WarmupStat(Base):
    """Daily email warmup statistics model"""
    __tablename__ = "warmup_stats"

    id = Column(Integer, primary_key=True, index=True)
    email_account_id = Column(Integer, ForeignKey("email_accounts.id"))
    date = Column(DateTime(timezone=True), server_default=func.now())
    emails_sent = Column(Integer, default=0)
    emails_received = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_replied = Column(Integer, default=0)
    emails_in_spam = Column(Integer, default=0)
    open_rate = Column(Float, default=0.0)
    reply_rate = Column(Float, default=0.0)
    spam_rate = Column(Float, default=0.0)
    deliverability_score = Column(Float, default=0.0)
    
    # Relationships
    email_account = relationship("EmailAccount", back_populates="warmup_stats")
    
    def __repr__(self):
        return f"<WarmupStat for {self.email_account_id} on {self.date}>"

class WarmupEmail(Base):
    """Email sent during warmup process"""
    __tablename__ = "warmup_emails"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), unique=True, index=True)
    sender_id = Column(Integer, ForeignKey("email_accounts.id"))
    recipient_id = Column(Integer, ForeignKey("email_accounts.id"))
    subject = Column(String(255))
    body = Column(Text)
    status = Column(String(50))  # sent, delivered, opened, replied, failed
    is_reply = Column(Boolean, default=False)
    in_spam = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    replied_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sender = relationship("EmailAccount", back_populates="sent_emails", foreign_keys=[sender_id])
    recipient = relationship("EmailAccount", back_populates="received_emails", foreign_keys=[recipient_id])
    
    def __repr__(self):
        return f"<WarmupEmail {self.message_id}>"

class DomainDNSRecord(Base):
    """DNS records for email domains"""
    __tablename__ = "dns_records"

    id = Column(Integer, primary_key=True, index=True)
    email_account_id = Column(Integer, ForeignKey("email_accounts.id"))
    record_type = Column(String(10))  # SPF, DKIM, DMARC
    record_name = Column(String(255))
    record_value = Column(Text)
    is_verified = Column(Boolean, default=False)
    last_checked = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    email_account = relationship("EmailAccount", back_populates="dns_records")
    
    def __repr__(self):
        return f"<DomainDNSRecord {self.record_type} for {self.email_account_id}>" 