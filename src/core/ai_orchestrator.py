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
            "contract": hand_data.get('contract', 'Pass')
        }

        # --- UPDATED PROMPT: OPENING VS RESPONDING DISTINCTION ---
        prompt = f"""
        You are an expert Bridge Teacher (Audrey Grant/SAYC style).
        Analyze this deal based strictly on the provided FACTS.
        
        CONTEXT DATA:
        {json.dumps(context_payload, indent=2)}

        CRITICAL EVALUATION RULES:
        1. **Points:** Use 'total_points' (HCP + Length) for opening decisions.
        2. **Weak 2 Bids:** Check suit quality (2 of top 3 honors OR 3 of top 5).
        3. **Game Contracts:** 3NT, 4H, 4S, 5C, 5D. (4D is NOT Game).
        4. **SAYC MAJOR SUIT RULES (STRICT):**
           - **OPENER:** MUST have 5+ cards to OPEN 1H or 1S. (If 4-4, open 1D or 1C).
           - **RESPONDER:** May respond 1H or 1S with only 4+ cards over a minor suit opening. THIS IS CORRECT SAYC.
           - **DO NOT** critique a responder for bidding a 4-card major over 1C/1D.

        TASK:
        Output strict JSON with these specific sections:

        1. VERDICT: Short phrase (e.g., "OPTIMAL CONTRACT", "MISSED GAME").
        
        2. ACTUAL_CRITIQUE: A list of 2-3 concise strings criticizing the actual play.
        
        3. BASIC_SECTION (The Fundamentals):
           - "analysis": Explanation of the Standard American approach.
           - "recommended_auction": A LIST OF OBJECTS representing the ideal sequence.
             Format: {{ "bid": "1H", "explanation": "Shows 6+ pts, 4+ Hearts (Responder)." }}
           
        4. ADVANCED_SECTION (The Master Class):
           - "analysis": Deeper look (Splinters, 2/1, etc.).
           - "sequence": A LIST OF OBJECTS for the advanced sequence (or null).

        5. COACHES_CORNER:
           - List of objects: {{ "player": "North", "topic": "...", "category": "Review" }}

        OUTPUT JSON FORMAT:
        {{
            "verdict": "...",
            "actual_critique": ["...", "..."],
            "basic_section": {{
                "analysis": "...",
                "recommended_auction": [
                    {{ "bid": "...", "explanation": "..." }}
                ]
            }},
            "advanced_section": {{
                "analysis": "...",
                "sequence": [ {{ "bid": "...", "explanation": "..." }} ]
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
        """
        Validates AI logic against Python math.
        """
        # 1. Check Game vs Part-Score
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

        # 2. Check 5-Card Major Rule (OPENER ONLY)
        try:
            recommended = analysis.get('basic_section', {}).get('recommended_auction', [])
            if recommended:
                first_bid_obj = recommended[0]
                first_bid = first_bid_obj['bid']
                
                # Identify if OPENING is 1H or 1S
                if first_bid in ['1H', '1S']:
                    dealer_seat = facts.get('dealer', 'South')
                    # Get Dealer's hand stats
                    dealer_hand = facts['hands'][dealer_seat]['stats']['cards']
                    
                    suit_char = first_bid[1] # 'H' or 'S'
                    suit_length = len(dealer_hand.get(suit_char, ''))
                    
                    if suit_length < 5:
                        logger.warning(f"RED TEAM: AI suggested OPENING {first_bid} with only {suit_length} cards!")
                        # FORCE CORRECTION
                        analysis['actual_critique'].insert(0, f"⚠️ AI ERROR FIXED: Cannot OPEN {first_bid} with only {suit_length} cards (SAYC requires 5).")
                        analysis['basic_section']['analysis'] += f" [RED TEAM NOTE: Opening {first_bid} requires 5 cards. A minor suit opening was required.]"
        except Exception as e:
            logger.error(f"Red Team Major Check failed: {e}")

        return analysis