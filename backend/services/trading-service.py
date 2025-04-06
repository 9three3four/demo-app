from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import asyncio

from ..db.database import get_db
from ..db.models import User, Order, TradingAccount, PriceHistory, OrderStatus, OrderType
from ..schemas.schemas import (
    OrderCreate, OrderResponse, PriceHistoryResponse,
    MarketDataResponse
)
from ..utils.logger import logger, log_execution_time
from .user_service import get_current_user
from .risk_engine import validate_order_risk

router = APIRouter()

@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
@log_execution_time(logger)
async def create_order(
    order_data: OrderCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new trading order."""
    trading_account = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id
    ).first()
    
    if not trading_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trading account not found"
        )
    
    if not trading_account.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trading account not verified"
        )
    
    risk_validation = await validate_order_risk(order_data, trading_account)
    if not risk_validation["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=risk_validation["message"]
        )
    
    try:
        new_order = Order(
            user_id=current_user.id,
            trading_account_id=trading_account.id,
            symbol=order_data.symbol,
            order_type=order_data.order_type,
            quantity=float(order_data.quantity),
            price=float(order_data.price) if order_data.price else None,
            status=OrderStatus.PENDING
        )
        
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        
        background_tasks.add_task(
            process_order,
            order_id=new_order.id,
            db=db
        )
        
        logger.info(
            "Order created successfully",
            extra={
                "props": {
                    "order_id": new_order.id,
                    "user_id": current_user.id,
                    "symbol": order_data.symbol
                }
            }
        )
        
        return new_order
        
    except Exception as e:
        db.rollback()
        logger.error(
            f"Error creating order: {str(e)}",
            extra={
                "props": {
                    "user_id": current_user.id,
                    "symbol": order_data.symbol
                }
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating order"
        )

@router.get("/orders", response_model=List[OrderResponse])
@log_execution_time(logger)
async def get_user_orders(
    status: Optional[OrderStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's orders with optional status filter."""
    query = db.query(Order).filter(Order.user_id == current_user.id)
    
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(Order.created_at.desc()).all()
    return orders

@router.get("/orders/{order_id}", response_model=OrderResponse)
@log_execution_time(logger)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific order details."""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order

@router.delete("/orders/{order_id}", status_code=status.HTTP_200_OK)
@log_execution_time(logger)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a pending order."""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order in {order.status.value} status"
        )
    
    try:
        order.status = OrderStatus.CANCELLED
        db.commit()
        db.refresh(order)
        
        logger.info(
            "Order cancelled successfully",
            extra={
                "props": {
                    "order_id": order.id,
                    "user_id": current_user.id
                }
            }
        )
        
        return {"message": "Order cancelled successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(
            f"Error cancelling order: {str(e)}",
            extra={
                "props": {
                    "order_id": order.id,
                    "user_id": current_user.id
                }
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cancelling order"
        )

@router.get("/market-data/{symbol}", response_model=MarketDataResponse)
@log_execution_time(logger)
async def get_market_data(symbol: str, db: Session = Depends(get_db)):
    """Get current market data for a symbol."""
    latest_price = db.query(PriceHistory).filter(
        PriceHistory.symbol == symbol
    ).order_by(
        PriceHistory.timestamp.desc()
    ).first()
    
    if not latest_price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No market data found for symbol {symbol}"
        )
    
    previous_day = db.query(PriceHistory).filter(
        PriceHistory.symbol == symbol,
        PriceHistory.timestamp < latest_price.timestamp
    ).order_by(
        PriceHistory.timestamp.desc()
    ).first()
    
    daily_change = 0
    if previous_day:
        daily_change = (
            (latest_price.close_price - previous_day.close_price)
            / previous_day.close_price
        ) * 100
    
    return MarketDataResponse(
        symbol=symbol,
        current_price=latest_price.close_price,
        daily_change=daily_change,
        daily_volume=latest_price.volume,
        last_updated=latest_price.timestamp
    )

async def process_order(order_id: int, db: Session):
    """Background task to process orders."""
    await asyncio.sleep(1)  # Simulate processing time
    
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order or order.status != OrderStatus.PENDING:
            return
        
        order.status = OrderStatus.EXECUTED
        order.executed_at = datetime.utcnow()
        db.commit()
        
        logger.info(
            "Order processed successfully",
            extra={
                "props": {
                    "order_id": order.id,
                    "status": order.status.value
                }
            }
        )
        
    except Exception as e:
        db.rollback()
        logger.error(
            f"Error processing order: {str(e)}",
            extra={"props": {"order_id": order_id}},
            exc_info=True
        )
        
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                order.status = OrderStatus.FAILED
                db.commit()
        except Exception as update_error:
            logger.error(
                f"Error updating failed order status: {str(update_error)}",
                extra={"props": {"order_id": order_id}},
                exc_info=True
            )