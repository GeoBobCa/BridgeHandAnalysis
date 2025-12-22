import os
import json
import re
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
from loguru import logger
from google import genai
from google.genai import types

# --- CONFIGURATION SECTION ---
AI_CONFIG = {
    "model_name": "gemini-flash-latest",
    "temperature": 0.4,  # RESTORED: Allows for judgment, shape valuation, and nuance.
    "response_mime_type": "application/json",
    "env_file_location": ".env"
}

class AIOrchestrator:
    
    def __init__(self):
        env_path = Path(__file__).resolve().parent.parent.parent / AI_CONFIG["env_file_location"]
        load_dotenv(dotenv_path=env_path)
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Missing GEMINI_API_KEY")
        logger.info("*** PRODUCTION MODE: Google GenAI Client Initialized ***")
        self.client = genai.Client(api_key=self.api_key)

    def analyze_hand(self, hand_data: Dict, math_results: Dict, dds_data: Dict = None) -> Dict:
        deal_id = hand_data.get('board', 'Unknown')
        logger.info(f"Sending deal {deal_id} to Gemini...")

        context_payload = {
            "dealer": hand_data.get('dealer'),
            "vulnerability": hand_data.get('vulnerability'),
            "hands": hand_data['hands'],
            "auction_history": hand_data.get('auction', []),
            "contract": hand_data.get('contract', 'Pass'),
            "double_dummy_truth": dds_data
        }

        # --- BALANCED COACH PROMPT ---
        prompt = f"""
        You are an expert Bridge Teacher (Audrey Grant/SAYC style).
        
        CONTEXT DATA:
        {json.dumps(context_payload, indent=2)}

        GUIDELINES:
        1. **Valuation:** Use Total Points (HCP + Length + Shortness). A shapely 11-count is often a better opener than a flat 12-count.
        2. **SAYC Standards:** 5-card majors for opening. 2/1 Game Forcing is active.
        3. **Double Dummy Reality:** Check 'double_dummy_truth'. 
           - If a contract goes down in theory but is a good percentage bid, PRAISE the decision. 
           - If a contract makes but is risky, note the luck.
           - Do not be result-oriented; be probability-oriented.

        CRITICAL OUTPUT FORMAT (For UI Compatibility):
        - You MUST list the recommended auction bids in STRICT CHRONOLOGICAL ORDER.
        - Start with the Dealer's first call.
        - **INCLUDE ALL PASSES:** (e.g., "Pass", "1H", "Pass", "2H", "Pass", "Pass", "Pass").

        TASK:
        Output strict JSON with these specific sections:

        1. VERDICT: Short phrase (e.g., "OPTIMAL CONTRACT", "MISSED GAME", "GOOD AGGRESSIVE BID").
        2. ACTUAL_CRITIQUE: 2-3 bullet points evaluating the actual players' decisions.
        3. BASIC_SECTION:
           - "analysis": Explain the hand's key features.
           - "recommended_auction": LIST of objects {{ "bid": "...", "explanation": "..." }}
        4. ADVANCED_SECTION:
           - "analysis": Discuss entries, defense, or advanced valuation.
           - "sequence": LIST of objects {{ "bid": "...", "explanation": "..." }}
        5. COACHES_CORNER: List of objects {{ "player": "...", "topic": "...", "category": "..." }}

        OUTPUT JSON FORMAT:
        {{
            "verdict": "...",
            "actual_critique": ["..."],
            "basic_section": {{
                "analysis": "...",
                "recommended_auction": [ {{ "bid": "1D", "explanation": "..." }} ]
            }},
            "advanced_section": {{
                "analysis": "...",
                "sequence": [ {{ "bid": "...", "explanation": "..." }} ]
            }},
            "coaches_corner": []
        }}
        """

        try:
            response = self.client.models.generate_content(
                model=AI_CONFIG["model_name"], 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type=AI_CONFIG["response_mime_type"],
                    temperature=AI_CONFIG["temperature"]
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
        # Standard Red Team checks maintained
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
        return analysis