from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..config.config import settings
from ..utils.logger import logger

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Enable connection health checks
    pool_size=5,  # Maximum number of connections in the pool
    max_overflow=10  # Maximum number of connections that can be created beyond pool_size
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for declarative models
Base = declarative_base()

def get_db():
    """
    Dependency to get database session.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Commit the transaction if no exception occurred
    except Exception as e:
        db.rollback()  # Rollback the transaction in case of exception
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()  # Always close the session

def init_db():
    """
    Initialize database by creating all tables.
    Should be called when application starts.
    """
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        raise