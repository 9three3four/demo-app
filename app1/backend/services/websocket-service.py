from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set, Optional, Any
import json
import asyncio
from datetime import datetime

from ..utils.logger import logger
from ..db.models import User, Order
from .user_service import get_current_user

class ConnectionManager:
    """
    Manage WebSocket connections and message broadcasting.
    """
    def __init__(self):
        # Store active connections: {user_id: {connection_id: WebSocket}}
        self.active_connections: Dict[int, Dict[str, WebSocket]] = {}
        # Store symbol subscriptions: {symbol: {user_id: {connection_id}}}
        self.symbol_subscriptions: Dict[str, Dict[int, Set[str]]] = {}
        
    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        connection_id: str
    ):
        """
        Connect a new WebSocket client.
        """
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        self.active_connections[user_id][connection_id] = websocket
        
        logger.info(
            "WebSocket client connected",
            extra={
                "props": {
                    "user_id": user_id,
                    "connection_id": connection_id
                }
            }
        )
    
    def disconnect(self, user_id: int, connection_id: str):
        """
        Disconnect a WebSocket client.
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].pop(connection_id, None)
            if not self.active_connections[user_id]:
                self.active_connections.pop(user_id)
        
        # Remove from symbol subscriptions
        for symbol in self.symbol_subscriptions:
            if user_id in self.symbol_subscriptions[symbol]:
                self.symbol_subscriptions[symbol][user_id].discard(connection_id)
                if not self.symbol_subscriptions[symbol][user_id]:
                    self.symbol_subscriptions[symbol].pop(user_id)
        
        logger.info(
            "WebSocket client disconnected",
            extra={
                "props": {
                    "user_id": user_id,
                    "connection_id": connection_id
                }
            }
        )
    
    def subscribe_to_symbol(
        self,
        symbol: str,
        user_id: int,
        connection_id: str
    ):
        """
        Subscribe a connection to a symbol's updates.
        """
        if symbol not in self.symbol_subscriptions:
            self.symbol_subscriptions[symbol] = {}
        if user_id not in self.symbol_subscriptions[symbol]:
            self.symbol_subscriptions[symbol][user_id] = set()
        self.symbol_subscriptions[symbol][user_id].add(connection_id)
        
        logger.info(
            "Client subscribed to symbol",
            extra={
                "props": {
                    "user_id": user_id,
                    "connection_id": connection_id,
                    "symbol": symbol
                }
            }
        )
    
    def unsubscribe_from_symbol(
        self,
        symbol: str,
        user_id: int,
        connection_id: str
    ):
        """
        Unsubscribe a connection from a symbol's updates.
        """
        if (symbol in self.symbol_subscriptions and
            user_id in self.symbol_subscriptions[symbol]):
            self.symbol_subscriptions[symbol][user_id].discard(connection_id)
            if not self.symbol_subscriptions[symbol][user_id]:
                self.symbol_subscriptions[symbol].pop(user_id)
            if not self.symbol_subscriptions[symbol]:
                self.symbol_subscriptions.pop(symbol)
        
        logger.info(
            "Client unsubscribed from symbol",
            extra={
                "props": {
                    "user_id": user_id,
                    "connection_id": connection_id,
                    "symbol": symbol
                }
            }
        )
    
    async def broadcast_price_update(
        self,
        symbol: str,
        price_data: Dict[str, Any]
    ):
        """
        Broadcast price update to all subscribed connections.
        """
        if symbol not in self.symbol_subscriptions:
            return
        
        message = {
            "type": "price_update",
            "symbol": symbol,
            "data": price_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for user_id in self.symbol_subscriptions[symbol]:
            for connection_id in self.symbol_subscriptions[symbol][user_id]:
                if (user_id in self.active_connections and
                    connection_id in self.active_connections[user_id]):
                    try:
                        await self.active_connections[user_id][connection_id].send_json(message)
                    except Exception as e:
                        logger.error(
                            f"Error broadcasting price update: {str(e)}",
                            extra={
                                "props": {
                                    "user_id": user_id,
                                    "connection_id": connection_id,
                                    "symbol": symbol
                                }
                            },
                            exc_info=True
                        )
    
    async def send_order_update(
        self,
        user_id: int,
        order: Order
    ):
        """
        Send order update to specific user's connections.
        """
        if user_id not in self.active_connections:
            return
        
        message = {
            "type": "order_update",
            "data": {
                "order_id": order.id,
                "symbol": order.symbol,
                "status": order.status.value,
                "executed_at": order.executed_at.isoformat() if order.executed_at else None
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for connection_id, websocket in self.active_connections[user_id].items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(
                    f"Error sending order update: {str(e)}",
                    extra={
                        "props": {
                            "user_id": user_id,
                            "connection_id": connection_id,
                            "order_id": order.id
                        }
                    },
                    exc_info=True
                )

# Create global connection manager
manager = ConnectionManager()

async def handle_websocket_connection(
    websocket: WebSocket,
    user: User = Depends(get_current_user)
):
    """
    Handle individual WebSocket connections.
    """
    connection_id = f"{user.id}-{datetime.utcnow().timestamp()}"
    
    try:
        await manager.connect(websocket, user.id, connection_id)
        
        while True:
            try:
                # Receive and process messages
                message = await websocket.receive_json()
                
                if message["type"] == "subscribe":
                    symbol = message["symbol"]
                    manager.subscribe_to_symbol(symbol, user.id, connection_id)
                    await websocket.send_json({
                        "type": "subscription_success",
                        "symbol": symbol
                    })
                
                elif message["type"] == "unsubscribe":
                    symbol = message["symbol"]
                    manager.unsubscribe_from_symbol(symbol, user.id, connection_id)
                    await websocket.send_json({
                        "type": "unsubscription_success",
                        "symbol": symbol
                    })
                
            except json.JSONDecodeError:
                logger.warning(
                    "Invalid message format",
                    extra={
                        "props": {
                            "user_id": user.id,
                            "connection_id": connection_id
                        }
                    }
                )
                continue
            
    except WebSocketDisconnect:
        manager.disconnect(user.id, connection_id)
    
    except Exception as e:
        logger.error(
            f"WebSocket error: {str(e)}",
            extra={
                "props": {
                    "user_id": user.id,
                    "connection_id": connection_id
                }
            },
            exc_info=True
        )
        manager.disconnect(user.id, connection_id)

async def start_price_feed():
    """
    Simulate price feed updates.
    In production, replace with real market data feed.
    """
    while True:
        try:
            # Simulate price updates for demo symbols
            symbols = ["BTC/USD", "ETH/USD", "AAPL", "GOOGL"]
            for symbol in symbols:
                if symbol in manager.symbol_subscriptions:
                    price_data = {
                        "price": 100 + (datetime.utcnow().second / 60) * 10,  # Dummy price
                        "volume": 1000,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await manager.broadcast_price_update(symbol, price_data)
            
            await asyncio.sleep(1)  # Update every second
            
        except Exception as e:
            logger.error(
                f"Error in price feed: {str(e)}",
                exc_info=True
            )
            await asyncio.sleep(5)  # Wait before retrying