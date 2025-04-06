from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import pyotp
from ..config.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# TOTP setup for 2FA
totp = pyotp.TOTP(settings.SECRET_KEY)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash.
    
    Args:
        plain_password: The password in plain text
        hashed_password: The hashed password to compare against
    
    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The password to hash
    
    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: The data to encode in the token
        expires_delta: Optional expiration time delta
    
    Returns:
        str: The encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: The JWT token to verify
    
    Returns:
        dict: The decoded token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def generate_totp() -> str:
    """
    Generate a new TOTP token for 2FA.
    
    Returns:
        str: The generated TOTP token
    """
    return totp.now()

def verify_totp(token: str) -> bool:
    """
    Verify a TOTP token.
    
    Args:
        token: The TOTP token to verify
    
    Returns:
        bool: True if token is valid, False otherwise
    """
    return totp.verify(token)

class SecurityUtils:
    """
    Utility class for security-related operations.
    """
    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """
        Validate password strength against security requirements.
        
        Args:
            password: The password to validate
        
        Returns:
            bool: True if password meets requirements, False otherwise
        """
        # Password must be at least 8 characters long
        if len(password) < 8:
            return False
        
        # Must contain at least one uppercase letter
        if not any(c.isupper() for c in password):
            return False
        
        # Must contain at least one lowercase letter
        if not any(c.islower() for c in password):
            return False
        
        # Must contain at least one digit
        if not any(c.isdigit() for c in password):
            return False
        
        # Must contain at least one special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False
        
        return True

    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """
        Sanitize input string to prevent injection attacks.
        
        Args:
            input_str: The input string to sanitize
        
        Returns:
            str: The sanitized input string
        """
        # Remove common SQL injection patterns
        dangerous_chars = ["'", '"', ';', '--', '/*', '*/']
        sanitized = input_str
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized.strip()