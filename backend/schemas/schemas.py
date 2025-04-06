from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from ..db.models import OrderStatus, OrderType

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        from ..utils.security import SecurityUtils
        if not SecurityUtils.validate_password_strength(v):
            raise ValueError(
                "Password must be at least 8 characters long and contain uppercase, "
                "lowercase, number and special character"
            )
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_2fa_enabled: bool
    created_at: datetime
    
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

class TradingAccountBase(BaseModel):
    currency: str = "USD"

class TradingAccountCreate(TradingAccountBase):
    pass

class TradingAccountResponse(TradingAccountBase):
    id: int
    user_id: int
    balance: float
    is_verified: bool
    created_at: datetime
    
    class Config:
        orm_mode = True

class OrderBase(BaseModel):
    symbol: str
    order_type: OrderType
    quantity: Decimal = Field(..., gt=0)
    price: Optional[Decimal] = Field(None, gt=0)

class OrderCreate(OrderBase):
    pass

class OrderResponse(OrderBase):
    id: int
    user_id: int
    trading_account_id: int
    status: OrderStatus
    created_at: datetime
    executed_at: Optional[datetime]
    
    class Config:
        orm_mode = True

class PriceHistoryBase(BaseModel):
    symbol: str
    open_price: Decimal
    close_price: Decimal
    high_price: Decimal
    low_price: Decimal
    volume: Decimal
    timestamp: datetime

class PriceHistoryCreate(PriceHistoryBase):
    pass

class PriceHistoryResponse(PriceHistoryBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class MarketDataResponse(BaseModel):
    symbol: str
    current_price: Decimal
    daily_change: Decimal
    daily_volume: Decimal
    last_updated: datetime

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)