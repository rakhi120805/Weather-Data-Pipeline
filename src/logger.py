"""
Logging Module
==============
Configures structured system logging for the pipeline. Logs are printed 
to the console and persisted in a rotating log file in the logs/ directory.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from src.config import config


def setup_logger(name: str = "weather_pipeline") -> logging.Logger:
    """
    Sets up and configures a system-wide logger.
    
    Args:
        name: Name of the logger, typically matching the file or module.
        
    Returns:
        A configured logging.Logger instance.
    """
    # Ensure logs folder exists
    log_dir = os.path.join(config.base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_filepath = os.path.join(log_dir, "pipeline.log")

    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if setup_logger is called multiple times
    if logger.hasHandlers():
        return logger

    # Set base level from configuration
    numeric_level = getattr(logging, config.log_level, logging.INFO)
    logger.setLevel(numeric_level)

    # Create formatters
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Console Handler (Standard Output)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler (Rotating log file - max 5MB per file, max 3 backups)
    file_handler = RotatingFileHandler(
        filename=log_filepath,
        maxBytes=5 * 1024 * 1024,  # 5 Megabytes
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logger()
