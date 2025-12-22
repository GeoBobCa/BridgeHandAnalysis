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
    "temperature": 0.2,  # Low enough to stop hallucinations, high enough for sentences
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

        # --- HYBRID PROTOCOL PROMPT ---
        prompt = f"""
        You are an expert Bridge Teacher.
        
        CONTEXT DATA:
        {json.dumps(context_payload, indent=2)}

        CRITICAL RULES (DO NOT BREAK):
        1. **OPENING BIDS:** - Standard 1-level Opening = 12+ HCP.
           - DO NOT recommend opening 9-11 HCP hands at the 1-level.
        2. **DDS REALITY CHECK:** - Look at 'double_dummy_truth'. 
           - If DDS says the hand makes 7 tricks in Spades, DO NOT recommend bidding 4S or 5S.
           - Recommend contracts that actually MAKE.
        3. **BIDDING LEGALITY:** - You cannot bid the same suit at the same level as the opponent (e.g., No 2H over 2H).
        4. **FORMAT:** List bids chronologically. INCLUDE ALL PASSES.

        SECTION GUIDELINES:
        - **BASIC SECTION:** STRICT Standard American. NO 2/1 Game Forcing. Keep it simple.
        - **ADVANCED SECTION:** 2/1 Game Forcing is ACTIVE here. Discuss modern conventions.

        TASK:
        Output strict JSON with these specific sections:

        1. VERDICT: "OPTIMAL", "OVERBID", "UNDERBID", "GOOD SAVE".
        2. ACTUAL_CRITIQUE: 2-3 bullet points.
        3. BASIC_SECTION:
           - "analysis": Standard evaluation.
           - "recommended_auction": LIST of objects {{ "bid": "...", "explanation": "..." }}
        4. ADVANCED_SECTION:
           - "analysis": 2/1 GF, advanced shape, entries.
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
        # Standard Red Team checks
        return analysis