from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from decimal import Decimal

from ..db.database import get_db
from ..db.models import User, Order, TradingAccount
from ..schemas.schemas import OrderCreate
from ..utils.logger import logger, log_execution_time
from .user_service import get_current_user

router = APIRouter()

# Risk limits configuration
RISK_LIMITS = {
    "max_order_value": 100000.0,  # Maximum value per order
    "max_daily_orders": 50,       # Maximum number of orders per day
    "max_position_size": 0.2,     # Maximum position size as percentage of account balance
    "min_account_balance": 100.0, # Minimum required account balance
    "max_leverage": 5.0,          # Maximum allowed leverage
}

async def validate_order_risk(
    order_data: OrderCreate,
    trading_account: TradingAccount,
    current_price: float = None  # In production, fetch from market data service
) -> Dict[str, Any]:
    """
    Validate order against risk management rules.
    
    Args:
        order_data: Order creation data
        trading_account: User's trading account
        current_price: Current market price (optional)
    
    Returns:
        Dict containing validation result and message
    """
    try:
        # If current_price not provided, use order price or simulate one
        price = current_price or float(order_data.price or 100.0)  # Default price for testing
        order_value = float(order_data.quantity) * price
        
        # Check minimum account balance
        if trading_account.balance < RISK_LIMITS["min_account_balance"]:
            return {
                "is_valid": False,
                "message": f"Account balance below minimum requirement of {RISK_LIMITS['min_account_balance']}"
            }
        
        # Check maximum order value
        if order_value > RISK_LIMITS["max_order_value"]:
            return {
                "is_valid": False,
                "message": f"Order value exceeds maximum limit of {RISK_LIMITS['max_order_value']}"
            }
        
        # Check position size as percentage of account balance
        position_size_ratio = order_value / trading_account.balance
        if position_size_ratio > RISK_LIMITS["max_position_size"]:
            return {
                "is_valid": False,
                "message": f"Position size exceeds {RISK_LIMITS['max_position_size']*100}% of account balance"
            }
        
        # Validate leverage
        required_margin = order_value / RISK_LIMITS["max_leverage"]
        if required_margin > trading_account.balance:
            return {
                "is_valid": False,
                "message": f"Insufficient margin for requested leverage"
            }
        
        return {
            "is_valid": True,
            "message": "Order passed risk validation"
        }
        
    except Exception as e:
        logger.error(
            f"Error in risk validation: {str(e)}",
            extra={
                "props": {
                    "trading_account_id": trading_account.id,
                    "order_data": order_data.dict()
                }
            },
            exc_info=True
        )
        return {
            "is_valid": False,
            "message": "Error performing risk validation"
        }

@router.get("/limits")
@log_execution_time(logger)
async def get_risk_limits(current_user: User = Depends(get_current_user)):
    """
    Get current risk management limits.
    """
    return RISK_LIMITS

@router.get("/account-risk")
@log_execution_time(logger)
async def get_account_risk_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get risk metrics for user's trading account.
    """
    trading_account = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id
    ).first()
    
    if not trading_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trading account not found"
        )
    
    # Get open orders
    open_orders = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.status == "pending"
    ).all()
    
    # Calculate risk metrics
    total_exposure = sum(
        float(order.quantity * (order.price or 100.0))  # Using dummy price if not set
        for order in open_orders
    )
    
    account_risk_metrics = {
        "account_balance": trading_account.balance,
        "total_exposure": total_exposure,
        "exposure_ratio": (total_exposure / trading_account.balance) if trading_account.balance > 0 else 0,
        "available_margin": trading_account.balance - (total_exposure / RISK_LIMITS["max_leverage"]),
        "open_orders_count": len(open_orders),
        "risk_limits": RISK_LIMITS
    }
    
    return account_risk_metrics

@router.get("/position-risk/{symbol}")
@log_execution_time(logger)
async def get_position_risk(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get risk metrics for a specific trading position.
    """
    # Get all orders for the symbol
    orders = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.symbol == symbol
    ).all()
    
    if not orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No positions found for symbol {symbol}"
        )
    
    # Calculate position metrics
    total_quantity = sum(
        float(order.quantity)
        for order in orders
        if order.status == "executed"
    )
    
    average_price = sum(
        float(order.quantity * (order.price or 100.0))  # Using dummy price if not set
        for order in orders
        if order.status == "executed"
    ) / total_quantity if total_quantity > 0 else 0
    
    position_metrics = {
        "symbol": symbol,
        "total_quantity": total_quantity,
        "average_price": average_price,
        "position_value": total_quantity * average_price,
        "executed_orders_count": len([o for o in orders if o.status == "executed"]),
        "pending_orders_count": len([o for o in orders if o.status == "pending"])
    }
    
    return position_metrics