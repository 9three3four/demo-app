from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta

from ..db.database import get_db
from ..db.models import User, TradingAccount
from ..schemas.schemas import (
    UserCreate, UserResponse, UserLogin, Token,
    TradingAccountCreate, TradingAccountResponse
)
from ..utils.security import (
    verify_password, get_password_hash,
    create_access_token, verify_token,
    generate_totp, verify_totp
)
from ..utils.logger import logger, log_execution_time
from ..config.config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@log_execution_time(logger)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user and create their trading account.
    """
    # Check if user already exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    try:
        # Create user
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.flush()  # Flush to get the user ID
        
        # Create trading account
        trading_account = TradingAccount(user_id=db_user.id)
        db.add(trading_account)
        db.commit()
        db.refresh(db_user)
        
        logger.info(
            f"User registered successfully: {user_data.email}",
            extra={"props": {"username": user_data.username}}
        )
        return db_user
        
    except Exception as e:
        db.rollback()
        logger.error(
            f"Error registering user: {str(e)}",
            extra={"props": {"email": user_data.email}},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user account"
        )

@router.post("/login", response_model=Token)
@log_execution_time(logger)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    logger.info(
        f"User logged in successfully: {user.email}",
        extra={"props": {"user_id": user.id}}
    )
    
    return Token(access_token=access_token)

@router.post("/2fa/enable", response_model=UserResponse)
@log_execution_time(logger)
async def enable_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enable 2FA for current user.
    """
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled"
        )
    
    try:
        current_user.is_2fa_enabled = True
        db.commit()
        db.refresh(current_user)
        
        logger.info(
            "2FA enabled successfully",
            extra={"props": {"user_id": current_user.id}}
        )
        return current_user
        
    except Exception as e:
        db.rollback()
        logger.error(
            f"Error enabling 2FA: {str(e)}",
            extra={"props": {"user_id": current_user.id}},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error enabling 2FA"
        )

@router.get("/me", response_model=UserResponse)
@log_execution_time(logger)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information.
    """
    return current_user

@router.get("/me/trading-account", response_model=TradingAccountResponse)
@log_execution_time(logger)
async def get_trading_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's trading account information.
    """
    trading_account = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id
    ).first()
    
    if not trading_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trading account not found"
        )
    
    return trading_account