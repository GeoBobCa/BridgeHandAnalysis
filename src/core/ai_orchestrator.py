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
    """
    Manages interactions with Google Gemini and performs 'Red Team' validation
    to ensure Bridge logic (Game vs Part-Score) is accurate.
    """
    
    def __init__(self):
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)

        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.error("GEMINI_API_KEY not found.")
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

        # --- UPDATED PROMPT: Requesting Explanations for Bids ---
        prompt = f"""
        You are an expert Bridge Teacher (Audrey Grant style).
        Analyze this deal based strictly on the provided FACTS.
        
        CONTEXT DATA:
        {json.dumps(context_payload, indent=2)}

        CRITICAL EVALUATION RULES:
        1. **Points:** Use 'total_points' (HCP + Length) for opening decisions.
        2. **Weak 2 Bids:** If a player opens a Weak 2, verify suit quality (2 of top 3 honors OR 3 of top 5).
           - If quality is bad, CRITIQUE IT in 'actual_critique'.
        3. **Game Contracts:** 3NT, 4H, 4S, 5C, 5D. (4D is NOT Game).

        TASK:
        Output strict JSON with these specific sections:

        1. VERDICT: Short phrase (e.g., "OPTIMAL CONTRACT", "MISSED GAME").
        
        2. ACTUAL_CRITIQUE: A list of 2-3 concise strings criticizing the actual play.
        
        3. BASIC_SECTION (The Fundamentals):
           - "analysis": Simple explanation of the Standard American approach.
           - "recommended_auction": A LIST OF OBJECTS representing the ideal sequence.
             Format: {{ "bid": "1H", "explanation": "Shows 12-20 pts, 5+ Hearts." }}
           
        4. ADVANCED_SECTION (The Master Class):
           - "analysis": Deeper look (Splinters, 2/1, etc.).
           - "sequence": A LIST OF OBJECTS for the advanced sequence (or null).
             Format: {{ "bid": "4H", "explanation": "Fast Arrival, shows minimum hand." }}

        5. COACHES_CORNER:
           - List of objects: {{ "player": "North", "topic": "...", "category": "Review" }}

        OUTPUT JSON FORMAT:
        {{
            "verdict": "...",
            "actual_critique": ["...", "..."],
            "basic_section": {{
                "analysis": "...",
                "recommended_auction": [
                    {{ "bid": "1D", "explanation": "..." }},
                    {{ "bid": "1S", "explanation": "..." }}
                ]
            }},
            "advanced_section": {{
                "analysis": "...",
                "sequence": [
                    {{ "bid": "...", "explanation": "..." }}
                ]
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
                return {"error": "Empty response from AI"}

        except Exception as e:
            logger.error(f"Gemini API Call failed: {e}")
            return {"error": str(e)}

    def _red_team_scan(self, analysis: Dict, facts: Dict) -> Dict:
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
                    analysis['actual_critique'].insert(0, f"Red Team Correction: {contract} is a part-score, not game.")
        return analysis