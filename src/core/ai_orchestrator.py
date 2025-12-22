import os
import json
import re
from pathlib import Path
from typing import Dict, List
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

        # --- SIMPLIFIED PROMPT (No explicit player labels) ---
        prompt = f"""
        You are an expert Bridge Teacher (Audrey Grant/SAYC style).
        
        CONTEXT DATA:
        {json.dumps(context_payload, indent=2)}

        CRITICAL RULES:
        1. **SAYC Logic:** Opener needs 5+ cards for Majors. Responder needs 4+.
        2. **DDS Truth:** Use 'double_dummy_truth' to validate your advice.
        3. **AUCTION FORMAT (CRITICAL):** - You MUST list the bids in strict chronological order starting with the Dealer.
           - **INCLUDE ALL PASSES:** If the auction is "1S - Pass - 4S", you MUST list the Pass. Do not skip opponents.
           - Format: Simple list of objects {{ "bid": "...", "explanation": "..." }}

        TASK:
        Output strict JSON with these specific sections:

        1. VERDICT: Short phrase (e.g., "OPTIMAL CONTRACT", "MISSED GAME").
        2. ACTUAL_CRITIQUE: 2-3 concise strings.
        3. BASIC_SECTION:
           - "analysis": Standard American explanation.
           - "recommended_auction": LIST of objects {{ "bid": "...", "explanation": "..." }}
           
        4. ADVANCED_SECTION:
           - "analysis": Advanced concepts.
           - "sequence": LIST of objects {{ "bid": "...", "explanation": "..." }} (Include ALL passes!)

        5. COACHES_CORNER: List of objects {{ "player": "...", "topic": "...", "category": "..." }}

        OUTPUT JSON FORMAT:
        {{
            "verdict": "...",
            "actual_critique": ["..."],
            "basic_section": {{
                "analysis": "...",
                "recommended_auction": [
                    {{ "bid": "1D", "explanation": "..." }}
                ]
            }},
            "advanced_section": {{
                "analysis": "...",
                "sequence": [ 
                    {{ "bid": "...", "explanation": "..." }} 
                ]
            }},
            "coaches_corner": []
        }}
        """

        try:
            # NO SLEEP NEEDED FOR PAID PLAN
            response = self.client.models.generate_content(
                model='gemini-flash-latest', 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    temperature=0.1 # Keep strict logic
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
    