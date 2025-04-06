from fastapi import FastAPI, Request, status, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import time
from datetime import datetime
import asyncio

from .config.config import settings
from .utils.logger import logger, log_execution_time
from .db.database import init_db
from .services import user_service, trading_service, risk_engine
from .services.websocket_service import handle_websocket_connection, start_price_feed

# Create FastAPI instance
app = FastAPI(
    title=settings.APP_NAME,
    description="Trading Platform API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log request details
    logger.info(
        "Request processed",
        extra={
            "props": {
                "method": request.method,
                "url": str(request.url),
                "process_time": process_time,
                "status_code": response.status_code
            }
        }
    )
    return response

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(
        "Validation error",
        extra={
            "props": {
                "errors": exc.errors(),
                "body": exc.body,
                "url": str(request.url)
            }
        }
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "error_code": "VALIDATION_ERROR",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(
        "Database error",
        extra={
            "props": {
                "error": str(exc),
                "url": str(request.url)
            }
        }
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_code": "DATABASE_ERROR",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Health check endpoint
@app.get("/health")
@log_execution_time(logger)
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Include routers
app.include_router(
    user_service.router,
    prefix="/api/v1/users",
    tags=["users"]
)

app.include_router(
    trading_service.router,
    prefix="/api/v1/trading",
    tags=["trading"]
)

app.include_router(
    risk_engine.router,
    prefix="/api/v1/risk",
    tags=["risk"]
)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handle_websocket_connection(websocket)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Trading Platform API")
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized successfully")
        
        # Start price feed in background
        asyncio.create_task(start_price_feed())
        logger.info("Price feed started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}", exc_info=True)
        raise

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Trading Platform API")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )