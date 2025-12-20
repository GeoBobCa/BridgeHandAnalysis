# src/utils/paths.py (Update)
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "bridge_master.db"
INPUTS_DIR = ROOT_DIR / "inputs"
ARCHIVES_DIR = DATA_DIR / "archives"
PROCESSED_DIR = DATA_DIR / "processed"  # <--- NEW LINE
LOGS_DIR = ROOT_DIR / "logs"

# Ensure they exist
for d in [DATA_DIR, INPUTS_DIR, ARCHIVES_DIR, PROCESSED_DIR, LOGS_DIR]: # <--- Add PROCESSED_DIR here
    d.mkdir(parents=True, exist_ok=True)