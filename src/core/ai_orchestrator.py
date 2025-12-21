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
        # 1. Force-load .env from the root directory
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

        # Prepare the context for the AI
        context_payload = {
            "dealer": hand_data.get('dealer'),
            "vulnerability": hand_data.get('vulnerability'),
            "hands": hand_data['hands'],
            "auction_history": hand_data.get('auction', []),
            "contract": hand_data.get('contract', 'Pass')
        }

        # --- THE MASTER PROMPT ---
        prompt = f"""
        You are an expert Bridge Teacher (Audrey Grant style).
        Analyze this deal based strictly on the provided FACTS.
        
        CONTEXT DATA:
        {json.dumps(context_payload, indent=2)}

        CRITICAL EVALUATION RULES:
        1. **Points:** Use 'total_points' (HCP + Length) for opening decisions.
        2. **Weak 2 Bids:** If a player opens a Weak 2, verify suit quality. 
           - MUST have 2 of the top 3 honors OR 3 of the top 5.
           - If they bid Weak 2 on a bad suit (e.g., Qxxxxx), YOU MUST CRITIQUE IT in the "actual_critique" section.
        3. **Game Contracts:** - 3NT, 4H, 4S, 5C, 5D. 
           - WARNING: 4C and 4D are PART-SCORES, not Game.

        TASK:
        Analyze this deal and output strict JSON with these specific sections:

        1. VERDICT: Short phrase (e.g., "OPTIMAL CONTRACT", "MISSED GAME", "OVERBID", "PART-SCORE MADE").
        
        2. ACTUAL_CRITIQUE: A list of 2-3 concise strings criticizing exactly what the players did wrong (or right) in the actual auction and play.
        
        3. BASIC_SECTION (The Fundamentals):
           - "analysis": A simple explanation of the correct Standard American approach.
           - "recommended_auction": A list of bids for the ideal Standard sequence (e.g. ["1D", "1S", "2NT"]).
           
        4. ADVANCED_SECTION (The Master Class):
           - "analysis": A deeper look (Splinters, 2/1, Squeezes, Signals). If nothing advanced applies, mention "No advanced conventions needed."
           - "sequence": An illustrated advanced bidding sequence if it differs from the basic one (or null).

        5. COACHES_CORNER (Personalized Learning):
           - A list of specific learning items.
           - "player": "North", "South", "East", "West", or "Pair NS".
           - "topic": The concept name (e.g. "Rule of 20", "Weak 2 Suit Quality").
           - "category": "Review" (Basics) or "Advanced" (Growth).

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
                "sequence": ["..."] 
            }},
            "coaches_corner": [
                {{ "player": "North", "topic": "...", "category": "Review" }}
            ]
        }}
        """

        try:
            # Short pause to prevent rate limiting on rapid loops
            time.sleep(0.5)

            response = self.client.models.generate_content(
                model='gemini-flash-latest', 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json'
                )
            )
            
            if response.text:
                # Parse AI JSON
                ai_analysis = json.loads(response.text)
                
                # Run the Red Team Validator to catch logic errors
                final_analysis = self._red_team_scan(ai_analysis, hand_data)
                
                return final_analysis
            else:
                return {"error": "Empty response from AI"}

        except Exception as e:
            logger.error(f"Gemini API Call failed: {e}")
            return {"error": str(e)}

    def _red_team_scan(self, analysis: Dict, facts: Dict) -> Dict:
        """
        A rigid code-validator to catch AI hallucinations regarding Game vs Part-Score.
        """
        contract = facts.get('contract', '')
        
        if contract and contract != 'Pass':
            # Regex to find Level (1-7) and Suit (C,D,H,S,NT)
            match = re.search(r'(\d)(NT|[SHDC])', contract)
            if match:
                level = int(match.group(1))
                suit = match.group(2)
                
                # Rigid Rules of Bridge
                is_major_game = (suit in ['H', 'S'] and level >= 4)
                is_minor_game = (suit in ['C', 'D'] and level >= 5)
                is_nt_game = (suit == 'NT' and level >= 3)
                
                is_actual_game = is_major_game or is_minor_game or is_nt_game
                
                # Check AI Verdict
                verdict_upper = analysis.get('verdict', '').upper()
                
                # ERROR 1: AI says "Game" but it was a Part-Score
                if not is_actual_game and "GAME" in verdict_upper and "MISSED" not in verdict_upper:
                    logger.warning(f"RED TEAM: Caught hallucination on {contract}. AI said Game. Fixing.")
                    analysis['verdict'] = "PART-SCORE MADE"
                    analysis['actual_critique'].insert(0, f"Red Team Correction: {contract} is a part-score, not game.")

        return analysis

if __name__ == "__main__":
    try:
        orch = AIOrchestrator()
        print("SUCCESS: AI Client initialized with Red Team protocols.")
    except Exception as e:
        print(f"FAILURE: {e}")