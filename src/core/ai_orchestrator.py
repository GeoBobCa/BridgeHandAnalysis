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
    "temperature": 0.15,  # Slightly bumped to allow for "praise" logic, but still strict
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

        # --- UPDATED PROMPT: STRICT SAYC & BALANCED GRADING ---
        prompt = f"""
        You are an expert Bridge Teacher playing Standard American Yellow Card (SAYC).
        
        CONTEXT DATA:
        {json.dumps(context_payload, indent=2)}

        STRICT BIDDING RULES (SAYC):
        1. **OPENING BIDS:** - 1-level suit opening requires 12+ HCP (or very strong 11). 
           - **NEVER** recommend opening 1-level with 9 HCP.
           - Preempts (2-level, 3-level) require long suits (6+ cards) and weak points (6-10).
        2. **MAJORS:** Opener needs 5+ cards for 1H/1S. Responder needs 4+.
        3. **GAME FORCING:** 2/1 is ON (Game Forcing). 1NT Opening is 15-17.

        LOGIC & EVALUATION GUIDELINES:
        1. **USE THE TRUTH:** Look at 'double_dummy_truth'. If it says 4S makes 10 tricks, DO NOT suggest stopping in 2NT unless the bidding makes reaching 4S impossible.
           - If Game makes but is less than 50% probability, note it as "Lucky."
           - If Game makes and is >50%, criticize stopping low.
        2. **BE FAIR:** If the actual auction reached the correct contract, grade it "OPTIMAL" or "WELL BID." Do not look for minor flaws just to be critical.
        3. **AUCTION FORMAT:** List bids chronologically, starting with Dealer. INCLUDE ALL PASSES.

        TASK:
        Output strict JSON with these specific sections:

        1. VERDICT: "OPTIMAL CONTRACT", "MISSED GAME", "OVERBID", or "GOOD PART-SCORE".
        2. ACTUAL_CRITIQUE: 2-3 balanced bullet points. Praise good judgment; correct errors.
        3. BASIC_SECTION:
           - "analysis": Explain the hand for a beginner.
           - "recommended_auction": LIST of objects {{ "bid": "...", "explanation": "..." }}
        4. ADVANCED_SECTION:
           - "analysis": Advanced concepts (evaluation, entries, defense).
           - "sequence": LIST of objects {{ "bid": "...", "explanation": "..." }} (Include ALL passes!)
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
        contract = facts.get('contract', '')
        if contract and contract != 'Pass':
            match = re.search(r'(\d)(NT|[SHDC])', contract)
            if match:
                level = int(match.group(1))
                suit = match.group(2)
                is_game = (suit in ['H','S'] and level>=4) or (suit in ['C','D'] and level>=5) or (suit=='NT' and level>=3)
                
                verdict = analysis.get('verdict', '').upper()
                # If DDS says game makes but verdict says missed...
                # (Logic can be expanded here, but kept simple for now)
                
        return analysis
    