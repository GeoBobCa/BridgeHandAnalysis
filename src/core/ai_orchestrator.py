import os
import json
import time
import re
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
from loguru import logger
from google import genai
from google.genai import types

class AIOrchestrator:
    """
    Manages interactions with Google Gemini and performs 'Red Team' validation.
    """
    
    def __init__(self):
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)

        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Missing GEMINI_API_KEY in .env")
            
        logger.info("*** PRODUCTION MODE: Google GenAI Client Initialized ***")
        self.client = genai.Client(api_key=self.api_key)

    def analyze_hand(self, hand_data: Dict, math_results: Dict) -> Dict:
        deal_id = hand_data.get('board', 'Unknown')
        logger.info(f"Sending deal {deal_id} to Gemini...")

        context_payload = {
            "dealer": hand_data.get('dealer'),
            "vulnerability": hand_data.get('vulnerability'),
            "hands": hand_data['hands'],
            "auction_history": hand_data.get('auction', []),
            "contract": hand_data.get('contract', 'Pass') # Ensure contract is passed
        }

        # --- UPDATED PROMPT: Bullet Points + Player Attribution ---
        prompt = f"""
        You are an expert Bridge Teacher (Audrey Grant style).
        
        CONTEXT DATA:
        {json.dumps(context_payload, indent=2)}

        TASK:
        Analyze this deal and output strict JSON.

        1. VERDICT: Short phrase (e.g., "OPTIMAL CONTRACT", "MISSED GAME").
        
        2. ANALYSIS_BULLETS: A list of 3-4 concise strings critiquing the auction/play.
           
        3. RECOMMENDED_AUCTION: 
           - If bidding was correct, return null.
           - If incorrect, return a list of bids (e.g., ["1H", "Pass", "4H"]).
           
        4. LEARNING_DATA: A list of specific learning items for the database.
           - "player": Who needs to learn this? ("North", "South", "East", "West", or "Pair NS")
           - "topic": The concept name (e.g., "Weak Two Bids", "Drawing Trumps")
           - "category": "Review" (Basic errors) or "Advanced" (Growth opportunities)

        OUTPUT JSON FORMAT:
        {{
            "verdict": "...",
            "analysis_bullets": ["...", "..."],
            "recommended_auction": ["..."] (or null),
            "learning_data": [
                {{ "player": "North", "topic": "Response to Takeout Double", "category": "Review" }},
                {{ "player": "South", "topic": "Splinter Bids", "category": "Advanced" }}
            ]
        }}
        """

        try:
            time.sleep(0.5)
            response = self.client.models.generate_content(
                model='gemini-flash-latest', 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json'
                )
            )
            
            if response.text:
                raw_analysis = json.loads(response.text)
                # --- RUN THE RED TEAM SCAN ---
                final_analysis = self._red_team_scan(raw_analysis, hand_data)
                return final_analysis
            else:
                return {"error": "Empty response from AI"}

        except Exception as e:
            logger.error(f"Gemini API Call failed: {e}")
            return {"error": str(e)}

    def _red_team_scan(self, analysis: Dict, facts: Dict) -> Dict:
        """
        A rigid code-validator to catch AI hallucinations before saving.
        """
        logger.info("Running Red Team validation...")
        
        # RULE 1: The "4 Diamonds is NOT Game" Rule
        # We extract the contract level and suit from the facts
        # (This assumes 'contract' string looks like '4D' or '3NT')
        contract = facts.get('contract', '')
        
        if contract and contract != 'Pass':
            # Regex to find Level (1-7) and Suit (C,D,H,S,NT)
            match = re.search(r'(\d)(NT|[SHDC])', contract)
            if match:
                level = int(match.group(1))
                suit = match.group(2)
                
                is_major_game = (suit in ['H', 'S'] and level >= 4)
                is_minor_game = (suit in ['C', 'D'] and level >= 5)
                is_nt_game = (suit == 'NT' and level >= 3)
                
                is_actual_game = is_major_game or is_minor_game or is_nt_game
                
                # Check if AI called a part-score "GAME"
                verdict_upper = analysis.get('verdict', '').upper()
                if not is_actual_game and "GAME" in verdict_upper and "MISSED" not in verdict_upper:
                    logger.warning(f"RED TEAM: Caught hallucination on {contract}. AI said Game. Fixing.")
                    analysis['verdict'] = "PART-SCORE MADE"
                    analysis['analysis_bullets'].append(f"(Red Team Correction: {contract} is a part-score, not game.)")

        return analysis

if __name__ == "__main__":
    try:
        orch = AIOrchestrator()
        print("SUCCESS: AI Client initialized with Red Team protocols.")
    except Exception as e:
        print(f"FAILURE: {e}")