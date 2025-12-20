import sys
from loguru import logger
from src.utils.paths import LOGS_DIR

def setup_logger():
    """Configures the logging format and file outputs."""
    logger.remove() # Remove default handler
    
    # Console Handler (Colorized, concise)
    logger.add(
        sys.stderr, 
        format="<green>{module}:{function}:{line}{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>", 
        level="INFO"
    )
    
    # File Handler (Detailed, rotation every 1 MB)
    log_file = LOGS_DIR / "bridge_master.log"
    logger.add(
        log_file, 
        rotation="1 MB", 
        retention="10 days", 
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} - {message}"
    )

    return logger