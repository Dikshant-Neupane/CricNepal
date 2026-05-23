"""
Logging configuration for CricNepal Analytics Platform

Provides centralized logging setup for all modules.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    Create and configure a logger instance.
    
    Args:
        name: Logger name (usually __name__ from calling module)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file name (stored in logs/ directory)
        console: Whether to output to console as well
        
    Returns:
        Configured logger instance
        
    Example:
        logger = setup_logger(__name__)
        logger.info("Loading match data")
        logger.error("Failed to load data", exc_info=True)
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_path = LOGS_DIR / log_file
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with default configuration.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    # Check if logger already exists and is configured
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Configure with defaults
        today = datetime.now().strftime('%Y%m%d')
        log_file = f"cricnepal_{today}.log"
        return setup_logger(name, log_file=log_file)
    return logger

# Pre-configured loggers for common modules
data_logger = setup_logger('cricnepal.data', log_file='data.log')
analytics_logger = setup_logger('cricnepal.analytics', log_file='analytics.log')
dashboard_logger = setup_logger('cricnepal.dashboard', log_file='dashboard.log')

__all__ = ['setup_logger', 'get_logger', 'data_logger', 'analytics_logger', 'dashboard_logger']
