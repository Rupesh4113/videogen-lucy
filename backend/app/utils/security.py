"""
Security and Cryptography Utilities for Videogen-Lucy.
Implements PBKDF2-HMAC-SHA256 password hashing, HMAC-SHA256 JWT tokens, and secure OTP generation.
Zero native C-extension dependencies, fully portable across all operating systems.
"""
import os
import hmac
import hashlib
import json
import base64
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from backend.app.config import settings


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ''
    return base64.urlsafe_b64decode((data + padding).encode('utf-8'))


def hash_password(password: str) -> str:
    """Hashes a plain password using PBKDF2-HMAC-SHA256 with a unique salt."""
    salt = os.urandom(16)
    iterations = 100_000
    hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    salt_b64 = _base64url_encode(salt)
    hash_b64 = _base64url_encode(hash_bytes)
    return f"pbkdf2_sha256${iterations}${salt_b64}${hash_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored PBKDF2 hash using constant-time comparison."""
    if not hashed_password or not hashed_password.startswith("pbkdf2_sha256$"):
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4:
            return False
        _, iterations_str, salt_b64, hash_b64 = parts
        iterations = int(iterations_str)
        salt = _base64url_decode(salt_b64)
        expected_hash = _base64url_decode(hash_b64)
        candidate_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, iterations)
        return hmac.compare_digest(expected_hash, candidate_hash)
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates an HMAC-SHA256 signed JSON Web Token (JWT)."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
    
    to_encode.update({"exp": int(expire.timestamp()), "iat": int(now.timestamp())})
    
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b64 = _base64url_encode(json.dumps(to_encode, separators=(',', ':')).encode('utf-8'))
    
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    secret = getattr(settings, "SECRET_KEY", "videogen_lucy_super_secret_jwt_key_2026").encode('utf-8')
    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates an HMAC-SHA256 signed JWT token."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        secret = getattr(settings, "SECRET_KEY", "videogen_lucy_super_secret_jwt_key_2026").encode('utf-8')
        expected_sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
        actual_sig = _base64url_decode(sig_b64)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        
        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        # Verify expiration
        exp = payload.get("exp")
        if exp:
            now_ts = int(datetime.now(timezone.utc).timestamp())
            if now_ts > exp:
                return None
                
        return payload
    except Exception:
        return None


def generate_otp_code(length: int = 6) -> str:
    """Generates a cryptographically secure numeric OTP code (e.g. '749281')."""
    return "".join(secrets.choice("0123456789") for _ in range(length))
