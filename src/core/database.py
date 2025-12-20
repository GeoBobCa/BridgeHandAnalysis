import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger

class DatabaseManager:
    """
    Manages the SQLite database for BridgeMaster.
    Handles schema creation and atomic transactions.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Establishes connection and enables Foreign Keys."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.db_path)
            # Critical: SQLite does not enforce FKs by default. We must enable it.
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.row_factory = sqlite3.Row # Access columns by name
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed.")

    def init_schema(self):
        """Creates the Tables if they do not exist."""
        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()

        # 1. TABLE: DEALS (The Immutable Hands)
        # We store pre-calculated math here for fast sorting/filtering in the UI.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY,
                dealer TEXT,
                vulnerability TEXT,
                hand_record_pbn TEXT,
                hands_json TEXT,  -- Full JSON of cards for querying
                
                -- Visualization Link (NEW)
                handviewer_url TEXT,
                
                -- North Math
                hcp_north INTEGER,
                dist_points_north INTEGER,
                
                -- South Math
                hcp_south INTEGER,
                dist_points_south INTEGER,
                
                -- East Math
                hcp_east INTEGER,
                dist_points_east INTEGER,
                
                -- West Math
                hcp_west INTEGER,
                dist_points_west INTEGER
            )
        """)

        # 2. TABLE: SESSIONS (The Context/Source)
        # Links a file import to the specific deals it contained.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT,
                import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                board_id TEXT,
                players_json TEXT, -- Names of N/S/E/W
                auction_json TEXT, -- The bidding history
                deal_id_fk TEXT,
                FOREIGN KEY(deal_id_fk) REFERENCES deals(deal_id)
            )
        """)

        # 3. TABLE: ANALYSES (The AI Results)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id_fk TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model_version TEXT,
                prompt_type TEXT, -- e.g. "Full_Analysis", "Bidding_Only"
                
                output_json TEXT, -- The raw JSON response from Gemini
                verified_status BOOLEAN, -- Did the python math check pass?
                
                FOREIGN KEY(deal_id_fk) REFERENCES deals(deal_id)
            )
        """)

        self.connection.commit()
        logger.info("Database schema initialized.")

    def _generate_deal_hash(self, hands_dict: Dict) -> str:
        """
        Creates a unique ID based on the cards. 
        Ensures if the same hand is imported twice, we don't duplicate it.
        """
        # Canonical string: N:Cards,E:Cards,S:Cards,W:Cards
        # Sort keys to ensure consistent order
        canonical = ""
        for direction in ['North', 'East', 'South', 'West']:
             # Flatten the list of suits ['AK', 'Q'] -> "AKQ"
             cards = "".join(hands_dict.get(direction, []))
             canonical += f"{direction}:{cards}|"
        
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    def save_deal(self, parsed_hand: Dict, math_results: Dict[str, Dict], handviewer_url: str) -> str:
        """
        Inserts a deal into the DB. Idempotent (ignores if already exists).
        
        Args:
            parsed_hand: The dict coming from BridgeParser
            math_results: The dict of dicts from BridgeMath {'North': {'hcp': 10...}}
            handviewer_url: The BBO URL string.
        
        Returns:
            The deal_id (hash) of the saved hand.
        """
        if not self.connection:
            self.connect()
            
        deal_id = self._generate_deal_hash(parsed_hand['hands'])
        
        try:
            # 1. Insert into DEALS (Ignore if exists)
            
            # Helper to safely get math values
            def get_m(direction, key):
                return math_results.get(direction, {}).get(key, 0)

            self.connection.execute("""
                INSERT OR IGNORE INTO deals (
                    deal_id, dealer, vulnerability, 
                    hands_json, handviewer_url,
                    hcp_north, dist_points_north,
                    hcp_south, dist_points_south,
                    hcp_east, dist_points_east,
                    hcp_west, dist_points_west
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                deal_id,
                parsed_hand.get('dealer', 'N'),
                parsed_hand.get('vulnerability', 'None'),
                json.dumps(parsed_hand['hands']),
                handviewer_url,
                
                get_m('North', 'hcp'), get_m('North', 'total_opener'),
                get_m('South', 'hcp'), get_m('South', 'total_opener'),
                get_m('East', 'hcp'),  get_m('East', 'total_opener'),
                get_m('West', 'hcp'),  get_m('West', 'total_opener')
            ))

            # 2. Insert into SESSIONS (Always insert, as it's a new occurrence)
            self.connection.execute("""
                INSERT INTO sessions (
                    source_file, board_id, players_json, auction_json, deal_id_fk
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                parsed_hand.get('source_file', 'unknown'),
                parsed_hand.get('board_id', ''),
                json.dumps(parsed_hand.get('players', {})),
                json.dumps(parsed_hand.get('auction', [])),
                deal_id
            ))
            
            self.connection.commit()
            return deal_id

        except sqlite3.Error as e:
            logger.error(f"Failed to save deal {deal_id}: {e}")
            self.connection.rollback()
            raise

    def get_all_deals(self) -> List[Dict]:
        """Fetches all deals for the UI grid."""
        cursor = self.connection.execute("SELECT * FROM deals")
        return [dict(row) for row in cursor.fetchall()]

if __name__ == "__main__":
    # Quick Test
    test_db = Path("test_bridge.db")
    db = DatabaseManager(test_db)
    db.init_schema()
    print("Schema created successfully.")
    
    # Cleanup
    db.close()
    if test_db.exists():
        import os
        os.remove(test_db)