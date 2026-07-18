"""
Configuration Module
====================
Responsible for loading, parsing, and validating environment variables 
from the .env file. Centralizes all settings to avoid hardcoding secrets.
"""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# Explicitly load environment variables from the .env file in the project root folder
load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    """Database Configuration supporting SQLite and PostgreSQL."""
    db_type: str = field(default_factory=lambda: os.getenv("DB_TYPE", "sqlite").lower())
    host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    name: str = field(default_factory=lambda: os.getenv("DB_NAME", "weather_db"))
    user: str = field(default_factory=lambda: os.getenv("DB_USER", "postgres"))
    password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))

    @property
    def connection_url(self) -> str:
        """Generate SQLAlchemy connection URL."""
        if self.db_type == "sqlite":
            # Store local SQLite database file in the project directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "weather.db")
            # Replace backslashes with forward slashes for SQLite URL compatibility on Windows
            db_path = db_path.replace("\\", "/")
            return f"sqlite:///{db_path}"
        else:
            return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass(frozen=True)
class AppConfig:
    """Global Application Configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("OPENWEATHER_API_KEY", ""))
    cities: List[str] = field(default_factory=list)
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())
    
    # Base directories (relative to project root)
    base_dir: str = field(default_factory=lambda: os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def __post_init__(self) -> None:
        """Validate critical configuration settings after initialization."""
        # Parse cities list from comma-separated string
        cities_raw = os.getenv("CITIES", "New York,London,Tokyo,Delhi,Sydney")
        parsed_cities = [city.strip() for city in cities_raw.split(",") if city.strip()]
        
        # We bypass frozen=True restriction using object.__setattr__ during instantiation
        object.__setattr__(self, "cities", parsed_cities)

        # Validate that API key exists (we will log a warning or raise an exception in production)
        if not self.api_key or self.api_key == "your_openweather_api_key_here":
            # We don't raise an exception here immediately to allow project initialization checks,
            # but we will raise/warn during the extraction step.
            pass


# Instantiated configuration object for global use
config = AppConfig()
