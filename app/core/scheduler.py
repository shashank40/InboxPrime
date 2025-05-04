import asyncio
import logging
import time
from datetime import datetime
from app.db.database import SessionLocal
from app.services.warmup_service import WarmupService

logger = logging.getLogger(__name__)

async def run_warmup_cycle_task():
    """
    Run a warmup cycle for all active and verified accounts
    """
    logger.info("Running scheduled warmup cycle")
    db = SessionLocal()
    try:
        result = await WarmupService.run_warmup_cycle(db)
        logger.info(f"Warmup cycle completed: {result['accounts_processed']} accounts processed, {result['total_emails_sent']} emails sent")
        if result['errors']:
            logger.warning(f"Warmup cycle encountered {len(result['errors'])} errors: {result['errors']}")
    except Exception as e:
        logger.error(f"Error in scheduled warmup cycle: {str(e)}")
    finally:
        db.close()

async def scheduler():
    """
    Scheduler function that runs tasks periodically
    """
    while True:
        # Get current hour
        current_hour = datetime.utcnow().hour
        
        # Run warmup cycle every 6 hours
        if current_hour % 6 == 0:
            await run_warmup_cycle_task()
        
        # Sleep until the next hour
        next_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        next_hour = next_hour.replace(hour=next_hour.hour + 1)
        sleep_seconds = (next_hour - datetime.utcnow()).total_seconds()
        await asyncio.sleep(sleep_seconds)

def start_scheduler():
    """
    Start the scheduler in a background task
    """
    loop = asyncio.get_event_loop()
    task = loop.create_task(scheduler())
    return task 