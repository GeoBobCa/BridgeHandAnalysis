import sys
from PyQt6.QtWidgets import QApplication
from pathlib import Path

# Local Imports
from src.utils.logger import setup_logger
from src.ui.main_window import MainWindow
from src.core.database import DatabaseManager 
from src.utils.paths import DB_PATH

logger = setup_logger()

def main():
    """
    Application Entry Point.
    """
    # 1. Setup Logging
    logger.info("Launching Bridge Master GUI...")

    # 2. Ensure Database Schema Exists
    # We initialize the DB manager just to ensure tables exist before the UI tries to read them.
    # This handles the "I deleted the DB file" scenario automatically.
    db_init = DatabaseManager(DB_PATH)
    db_init.init_schema()
    db_init.close()

    # 3. Launch PyQt App
    app = QApplication(sys.argv)
    
    # Apply a clean standard style
    app.setStyle("Fusion") 
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"GUI Crash: {e}")