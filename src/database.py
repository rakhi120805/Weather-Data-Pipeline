"""
Database Module
===============
Establishes the database connection using SQLAlchemy engine and session makers.
Defines the Object Relational Mapping (ORM) model for the weather_data table.
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from src.config import config
from src.logger import logger

# Create the Declarative Base class
Base = declarative_base()


class WeatherData(Base):
    """SQLAlchemy ORM Model for the weather_data table."""
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(100), nullable=False)
    country = Column(String(10), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    feels_like = Column(Float, nullable=False)
    humidity = Column(Integer, nullable=False)
    pressure = Column(Integer, nullable=False)
    wind_speed = Column(Float, nullable=False)
    visibility = Column(Integer, nullable=False)
    weather = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    cloudiness = Column(Integer, nullable=False)
    
    # Timestamps (mapped as DateTime objects in SQLAlchemy)
    sunrise = Column(DateTime, nullable=False)
    sunset = Column(DateTime, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    
    # Feature engineered derived columns
    temp_category = Column(String(10), nullable=False)
    humidity_category = Column(String(15), nullable=False)
    wind_category = Column(String(10), nullable=False)
    
    # Metadata audit timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    # Unique constraint representing our business key to allow safe idempotent loading
    __table_args__ = (
        UniqueConstraint("city", "timestamp", name="uq_city_timestamp"),
    )

    def __repr__(self) -> str:
        return f"<WeatherData(city='{self.city}', timestamp='{self.timestamp}', temp={self.temperature}°C)>"


# Central Database Manager
class DatabaseManager:
    """Manages the lifecycle of database engine and session connections."""

    def __init__(self) -> None:
        self.connection_url = config.db.connection_url
        self.db_type = config.db.db_type
        
        logger.info(f"Initializing Database connection pool to: {self.db_type}")
        
        # Configure engine. For SQLite, we add connect_args={'timeout': 15} to handle locks,
        # and echo=False (set to True to debug raw SQL queries)
        if self.db_type == "sqlite":
            self.engine = create_engine(
                self.connection_url, 
                connect_args={"check_same_thread": False}
            )
        else:
            self.engine = create_engine(
                self.connection_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True  # Automatically checks connection health before executing query
            )

        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )

    def init_db(self) -> None:
        """Runs DDL commands to create tables in the database if they don't exist."""
        try:
            logger.info("Running DDL metadata schemas to initialize database tables...")
            Base.metadata.create_all(self.engine)
            logger.info("Database tables initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize database tables: {e}")
            raise e

    def get_session(self):
        """Context manager style connection accessor for safe sessions."""
        session = self.SessionLocal()
        try:
            return session
        except Exception as e:
            session.close()
            raise e


# Instantiate database singleton
db_manager = DatabaseManager()
