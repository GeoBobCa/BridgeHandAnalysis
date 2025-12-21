import os
import json
import time
import re
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv
from loguru import logger
from google import genai
from google.genai import types

class AIOrchestrator:
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
            "contract": hand_data.get('contract', 'Pass')
        }

        # --- 3-TIER PROMPT STRUCTURE ---
        prompt = f"""
        You are an expert Bridge Teacher (Audrey Grant style).
        
        CONTEXT DATA:
        {json.dumps(context_payload, indent=2)}

        TASK:
        Analyze this deal and output strict JSON with these specific sections:

        1. VERDICT: Short phrase (e.g., "OPTIMAL CONTRACT", "MISSED GAME").
        
        2. ACTUAL_CRITIQUE: A list of 2-3 strings criticizing exactly what the players did wrong (or right) in the actual auction and play.
        
        3. BASIC_SECTION:
           - "analysis": A simple explanation of the correct Standard American approach.
           - "recommended_auction": A list of bids for the ideal Standard sequence (e.g. ["1D", "1S", "2NT"]).
           
        4. ADVANCED_SECTION:
           - "analysis": A deeper look (Splinters, 2/1, Squeezes, signals). If none apply, mention "No advanced conventions needed."
           - "sequence": An illustrated advanced bidding sequence if it differs from the basic one (or null).

        5. COACHES_CORNER: A list of specific learning items.
           - "player": "North", "South", "East", "West", or "Pair NS".
           - "topic": The concept name.
           - "category": "Review" or "Advanced".

        OUTPUT JSON FORMAT:
        {{
            "verdict": "...",
            "actual_critique": ["...", "..."],
            "basic_section": {{
                "analysis": "...",
                "recommended_auction": ["..."] 
            }},
            "advanced_section": {{
                "analysis": "...",
                "sequence": ["..."] (or null)
            }},
            "coaches_corner": [
                {{ "player": "North", "topic": "...", "category": "Review" }}
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
                return self._red_team_scan(json.loads(response.text), hand_data)
            else:
                return {"error": "Empty response"}

        except Exception as e:
            logger.error(f"Gemini API Call failed: {e}")
            return {"error": str(e)}

    def _red_team_scan(self, analysis: Dict, facts: Dict) -> Dict:
        # Simple Red Team Validator for Game/Part-Score
        contract = facts.get('contract', '')
        if contract and contract != 'Pass':
            match = re.search(r'(\d)(NT|[SHDC])', contract)
            if match:
                level = int(match.group(1))
                suit = match.group(2)
                is_game = (suit in ['H','S'] and level>=4) or (suit in ['C','D'] and level>=5) or (suit=='NT' and level>=3)
                
                verdict = analysis.get('verdict', '').upper()
                if not is_game and "GAME" in verdict and "MISSED" not in verdict:
                    analysis['verdict'] = "PART-SCORE MADE"
                    analysis['actual_critique'].insert(0, f"Red Team Note: {contract} is a part-score, not game.")
        return analysis