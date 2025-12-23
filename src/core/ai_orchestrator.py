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
    "temperature": 0.3,  # Strict enough for rules, smart enough for judgment
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

        # --- THE "IRONCLAD" PROMPT (v3.0) ---
        prompt = f"""
        You are an expert Bridge Teacher (Standard American / SAYC).
        
        CONTEXT DATA:
        {json.dumps(context_payload, indent=2)}

        MASTER RULE #1: THE "GAME HUNTER" MANDATE (Board 6 Fix)
        - Look at 'double_dummy_truth'. 
        - If DDS says a Game Contract (3NT, 4H, 4S, 5C, 5D) makes, you CANNOT recommend stopping in a part-score.
        - If Game is makeable but the players stopped low, Verdict MUST be "MISSED GAME".

        MASTER RULE #2: THE "DUCK" TEST (Board 11 Fix)
        - **Weak Twos:** If a hand has 6 cards and 6-10 HCP, it is a WEAK TWO (2D/2H/2S). 
        - Do NOT count "length points" to upgrade this to a 1-opener. Structure beats Valuation.
        - **Opening Criteria:** 1-level suit opening requires 12+ HCP (or 11 HCP + Rule of 20). Never open 9-10 HCP hands at 1-level.

        MASTER RULE #3: THE GOLDEN FIT (Board 15 Fix)
        - **Fit Requirement:** Do NOT recommend a final suit contract unless the partnership has a confirmed 8+ card fit.
        - If DDS shows Spades make (e.g. 3S) and Hearts don't, you MUST find the auction that reaches Spades. 
        - Do not strand players in a 7-card fit (like 1H) if a better fit exists.

        TASK:
        Output strict JSON with these specific sections:

        1. VERDICT: "OPTIMAL", "MISSED GAME", "OVERBID", "WRONG OPENER", "WRONG CONTRACT".
        2. ACTUAL_CRITIQUE: 2-3 bullet points.
        3. BASIC_SECTION (Standard American):
           - "analysis": Basic evaluation.
           - "recommended_auction": LIST of objects {{ "bid": "...", "explanation": "..." }}
        4. ADVANCED_SECTION (2/1 GF Active):
           - "analysis": 2/1 logic.
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
        return analysis