# debug_db.py
from src.utils.paths import DB_PATH
from src.core.database import DatabaseManager

print("-" * 50)
print(f"PYTHON IS WRITING TO:  {DB_PATH}")
print(f"Does file exist?       {DB_PATH.exists()}")
print("-" * 50)

if DB_PATH.exists():
    db = DatabaseManager(DB_PATH)
    db.connect()
    
    # Check Deals
    deals = db.connection.execute("SELECT count(*) FROM deals").fetchone()[0]
    print(f"Rows in 'deals' table:    {deals}")
    
    # Check Sessions
    sessions = db.connection.execute("SELECT count(*) FROM sessions").fetchone()[0]
    print(f"Rows in 'sessions' table: {sessions}")
    
    # Check for specific Data
    if deals > 0:
        sample = db.connection.execute("SELECT deal_id, dealer FROM deals LIMIT 1").fetchone()
        print(f"Sample Deal ID:           {sample[0]}")
        print(f"Sample Dealer:            {sample[1]}")
    else:
        print(">> THE DATABASE IS EMPTY.")
        
    db.close()
print("-" * 50)