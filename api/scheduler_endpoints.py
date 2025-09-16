"""
API endpoints for monitoring and controlling the automatic reply scheduler
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Create router for scheduler endpoints
scheduler_router = APIRouter(prefix="/scheduler", tags=["Automatic Reply Scheduler"])

@scheduler_router.get("/status")
async def get_scheduler_status() -> Dict[str, Any]:
    """Get current status of the automatic reply checking scheduler"""
    try:
        from services.automatic_reply_scheduler import get_reply_check_status
        status = get_reply_check_status()
        return {
            "status": "success",
            "scheduler_status": status
        }
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")

@scheduler_router.post("/start")
async def start_scheduler() -> Dict[str, Any]:
    """Start the automatic reply checking scheduler"""
    try:
        from services.automatic_reply_scheduler import start_automatic_reply_checking
        scheduler = start_automatic_reply_checking()
        return {
            "status": "success", 
            "message": "Automatic reply checking scheduler started",
            "config": scheduler.config
        }
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scheduler: {str(e)}")

@scheduler_router.post("/stop")
async def stop_scheduler() -> Dict[str, Any]:
    """Stop the automatic reply checking scheduler"""
    try:
        from services.automatic_reply_scheduler import stop_automatic_reply_checking
        stop_automatic_reply_checking()
        return {
            "status": "success",
            "message": "Automatic reply checking scheduler stopped"
        }
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduler: {str(e)}")

@scheduler_router.post("/trigger-manual-check")
async def trigger_manual_check() -> Dict[str, Any]:
    """Manually trigger a reply check (for testing)"""
    try:
        from services.automatic_reply_scheduler import get_scheduler
        scheduler = get_scheduler()
        
        # Trigger the check manually
        scheduler._check_all_introductory_emails()
        
        return {
            "status": "success",
            "message": "Manual reply check triggered successfully"
        }
    except Exception as e:
        logger.error(f"Error triggering manual check: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger manual check: {str(e)}")

@scheduler_router.get("/config")
async def get_scheduler_config() -> Dict[str, Any]:
    """Get current scheduler configuration"""
    try:
        from services.automatic_reply_scheduler import get_scheduler
        scheduler = get_scheduler()
        return {
            "status": "success",
            "config": scheduler.config
        }
    except Exception as e:
        logger.error(f"Error getting scheduler config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")

@scheduler_router.put("/config")
async def update_scheduler_config(new_config: Dict[str, Any]) -> Dict[str, Any]:
    """Update scheduler configuration (requires restart to take effect)"""
    try:
        # Here you could add logic to update environment variables or config file
        # For now, just return what would need to be updated
        return {
            "status": "success",
            "message": "Configuration update noted - restart required to take effect",
            "new_config": new_config,
            "note": "Update .env file and restart application for changes to take effect"
        }
    except Exception as e:
        logger.error(f"Error updating scheduler config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")