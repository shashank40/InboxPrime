import logging
import dns.resolver
import dns.exception
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import EmailAccount, DomainDNSRecord

logger = logging.getLogger(__name__)

class DNSService:
    """Service for DNS record verification"""
    
    @staticmethod
    def get_domain_from_email(email_address: str) -> str:
        """Extract domain from email address"""
        return email_address.split('@')[1]
    
    @staticmethod
    def generate_dns_records(email_account: EmailAccount) -> list:
        """Generate recommended DNS records for the email domain"""
        domain = DNSService.get_domain_from_email(email_account.email_address)
        
        # Generate SPF record
        spf_record = {
            "record_type": "SPF",
            "record_name": domain,
            "record_value": f'v=spf1 include:_spf.{domain} ~all',
            "is_verified": False
        }
        
        # Generate DKIM record
        dkim_selector = "mail"  # Default selector
        dkim_record = {
            "record_type": "DKIM",
            "record_name": f"{dkim_selector}._domainkey.{domain}",
            "record_value": "v=DKIM1; k=rsa; p=YOUR_PUBLIC_KEY_HERE",
            "is_verified": False
        }
        
        # Generate DMARC record
        dmarc_record = {
            "record_type": "DMARC",
            "record_name": f"_dmarc.{domain}",
            "record_value": "v=DMARC1; p=none; sp=none; adkim=r; aspf=r; fo=1; rua=mailto:dmarc@yourdomain.com;",
            "is_verified": False
        }
        
        return [spf_record, dkim_record, dmarc_record]
    
    @staticmethod
    async def verify_dns_records(db: Session, email_account_id: int) -> dict:
        """Verify DNS records for an email domain"""
        result = {
            "success": True,
            "verified": False,
            "records": [],
            "errors": []
        }
        
        try:
            # Get the email account
            email_account = db.query(EmailAccount).filter(
                EmailAccount.id == email_account_id
            ).first()
            
            if not email_account:
                result["success"] = False
                result["errors"].append("Email account not found")
                return result
            
            domain = DNSService.get_domain_from_email(email_account.email_address)
            
            # Get DNS records from database
            dns_records = db.query(DomainDNSRecord).filter(
                DomainDNSRecord.email_account_id == email_account_id
            ).all()
            
            if not dns_records:
                # Generate recommended DNS records
                record_data = DNSService.generate_dns_records(email_account)
                dns_records = []
                
                for data in record_data:
                    record = DomainDNSRecord(
                        email_account_id=email_account_id,
                        record_type=data["record_type"],
                        record_name=data["record_name"],
                        record_value=data["record_value"],
                        is_verified=False
                    )
                    db.add(record)
                    dns_records.append(record)
                
                db.commit()
                
                # Refresh records
                for record in dns_records:
                    db.refresh(record)
            
            # Verify each record
            all_verified = True
            
            for record in dns_records:
                record_result = {
                    "id": record.id,
                    "type": record.record_type,
                    "name": record.record_name,
                    "value": record.record_value,
                    "verified": False,
                    "error": None
                }
                
                try:
                    if record.record_type == "SPF":
                        # Verify SPF record
                        answers = dns.resolver.resolve(domain, 'TXT')
                        spf_found = False
                        
                        for rdata in answers:
                            txt_string = rdata.to_text()
                            if 'v=spf1' in txt_string:
                                spf_found = True
                                record.is_verified = True
                                record_result["verified"] = True
                                break
                        
                        if not spf_found:
                            record_result["error"] = "SPF record not found"
                            all_verified = False
                    
                    elif record.record_type == "DKIM":
                        # Extract selector from record name
                        selector = record.record_name.split('._domainkey')[0]
                        
                        # Verify DKIM record
                        try:
                            answers = dns.resolver.resolve(f"{selector}._domainkey.{domain}", 'TXT')
                            dkim_found = False
                            
                            for rdata in answers:
                                txt_string = rdata.to_text()
                                if 'v=DKIM1' in txt_string:
                                    dkim_found = True
                                    record.is_verified = True
                                    record_result["verified"] = True
                                    break
                            
                            if not dkim_found:
                                record_result["error"] = "DKIM record not found"
                                all_verified = False
                        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                            record_result["error"] = "DKIM record not found"
                            all_verified = False
                    
                    elif record.record_type == "DMARC":
                        # Verify DMARC record
                        try:
                            answers = dns.resolver.resolve(f"_dmarc.{domain}", 'TXT')
                            dmarc_found = False
                            
                            for rdata in answers:
                                txt_string = rdata.to_text()
                                if 'v=DMARC1' in txt_string:
                                    dmarc_found = True
                                    record.is_verified = True
                                    record_result["verified"] = True
                                    break
                            
                            if not dmarc_found:
                                record_result["error"] = "DMARC record not found"
                                all_verified = False
                        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                            record_result["error"] = "DMARC record not found"
                            all_verified = False
                
                except Exception as e:
                    logger.error(f"Error verifying DNS record: {str(e)}")
                    record_result["error"] = str(e)
                    all_verified = False
                
                record.last_checked = datetime.utcnow()
                result["records"].append(record_result)
            
            # Update email account verification status
            email_account.is_verified = all_verified
            email_account.verification_status = "verified" if all_verified else "failed"
            
            # Commit changes
            db.commit()
            
            result["verified"] = all_verified
            return result
        
        except Exception as e:
            logger.error(f"Failed to verify DNS records: {str(e)}")
            result["success"] = False
            result["errors"].append(f"Failed to verify DNS records: {str(e)}")
            return result 