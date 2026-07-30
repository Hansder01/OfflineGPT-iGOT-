from datetime import datetime, timedelta
from typing import Tuple, Dict, Any
from sqlalchemy.orm import Session
from backend.config import settings
from backend.models import RateLimitRecord

def check_rate_limit(db: Session, identifier: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Checks if identifier (user_id or IP) has exceeded the prompt limit.
    Returns (is_allowed, status_dict)
    """
    now = datetime.utcnow()
    window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS
    max_prompts = settings.RATE_LIMIT_PROMPTS

    record = db.query(RateLimitRecord).filter(RateLimitRecord.identifier == identifier).first()

    if not record:
        record = RateLimitRecord(
            identifier=identifier,
            request_count=1,
            window_start=now
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        
        remaining = max_prompts - 1
        reset_in_seconds = window_seconds
        return True, {
            "allowed": True,
            "current_count": 1,
            "max_prompts": max_prompts,
            "remaining": remaining,
            "window_seconds": window_seconds,
            "reset_in_seconds": reset_in_seconds,
            "cooldown_active": False
        }

    # Check if window expired
    elapsed = (now - record.window_start).total_seconds()

    if elapsed >= window_seconds:
        # Reset window
        record.request_count = 1
        record.window_start = now
        db.commit()
        
        return True, {
            "allowed": True,
            "current_count": 1,
            "max_prompts": max_prompts,
            "remaining": max_prompts - 1,
            "window_seconds": window_seconds,
            "reset_in_seconds": window_seconds,
            "cooldown_active": False
        }

    # Within current window
    if record.request_count >= max_prompts:
        cooldown_seconds = int(window_seconds - elapsed)
        return False, {
            "allowed": False,
            "current_count": record.request_count,
            "max_prompts": max_prompts,
            "remaining": 0,
            "window_seconds": window_seconds,
            "reset_in_seconds": cooldown_seconds,
            "cooldown_active": True,
            "message": f"Rate limit reached! Maximum {max_prompts} prompts allowed per {window_seconds // 60} minutes. Please wait {cooldown_seconds} seconds before trying again."
        }

    # Increment count
    record.request_count += 1
    db.commit()

    remaining = max_prompts - record.request_count
    reset_in_seconds = int(window_seconds - elapsed)

    return True, {
        "allowed": True,
        "current_count": record.request_count,
        "max_prompts": max_prompts,
        "remaining": remaining,
        "window_seconds": window_seconds,
        "reset_in_seconds": reset_in_seconds,
        "cooldown_active": False
    }

def get_rate_limit_info(db: Session, identifier: str) -> Dict[str, Any]:
    """Retrieves current rate limit status without incrementing count."""
    now = datetime.utcnow()
    window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS
    max_prompts = settings.RATE_LIMIT_PROMPTS

    record = db.query(RateLimitRecord).filter(RateLimitRecord.identifier == identifier).first()

    if not record:
        return {
            "current_count": 0,
            "max_prompts": max_prompts,
            "remaining": max_prompts,
            "window_seconds": window_seconds,
            "reset_in_seconds": 0,
            "cooldown_active": False
        }

    elapsed = (now - record.window_start).total_seconds()

    if elapsed >= window_seconds:
        return {
            "current_count": 0,
            "max_prompts": max_prompts,
            "remaining": max_prompts,
            "window_seconds": window_seconds,
            "reset_in_seconds": 0,
            "cooldown_active": False
        }

    remaining = max(0, max_prompts - record.request_count)
    reset_in_seconds = int(window_seconds - elapsed)
    cooldown_active = record.request_count >= max_prompts

    return {
        "current_count": record.request_count,
        "max_prompts": max_prompts,
        "remaining": remaining,
        "window_seconds": window_seconds,
        "reset_in_seconds": reset_in_seconds,
        "cooldown_active": cooldown_active
    }
