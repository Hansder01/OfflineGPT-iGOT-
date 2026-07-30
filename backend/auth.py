import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from backend.config import settings
from backend.models import User, UserSession

# Robust Password Hashing using PBKDF2_HMAC
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${pw_hash}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt, stored_hash = hashed_password.split('$')
        pw_hash = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return secrets.compare_digest(stored_hash, pw_hash)
    except Exception:
        return False

# JWT & Session Generation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_db_session(db: Session, user: User, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    db_session = UserSession(
        session_token=session_token,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
        is_active=True
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return session_token

def get_current_user_from_token(db: Session, token: str) -> Optional[User]:
    # Check DB Session first
    db_session = db.query(UserSession).filter(
        UserSession.session_token == token,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    
    if db_session:
        return db.query(User).filter(User.id == db_session.user_id, User.is_active == True).first()
    
    # Try decoding JWT Token
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
        return db.query(User).filter(User.id == user_id, User.is_active == True).first()
    except Exception:
        return None

def deactivate_session(db: Session, token: str):
    db_session = db.query(UserSession).filter(UserSession.session_token == token).first()
    if db_session:
        db_session.is_active = False
        db.commit()
