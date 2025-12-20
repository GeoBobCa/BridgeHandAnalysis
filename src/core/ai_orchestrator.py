import os
import json
import time
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv
from loguru import logger
from google import genai
from google.genai import types

class AIOrchestrator:
    """
    Manages interactions with Google Gemini using the google-genai SDK.
    """
    
    def __init__(self):
        # 1. Force-load .env
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

        # Context Setup
        context_payload = {
            "dealer": hand_data.get('dealer'),
            "vulnerability": hand_data.get('vulnerability'),
            "hands": hand_data['hands'],
            "auction_history": hand_data.get('auction', []),
            "play_history": hand_data.get('play', [])
        }

        # The "Rules-Based" Prompt
        prompt = f"""
        You are an expert Bridge Teacher (Audrey Grant style).
        Analyze the following deal based strictly on the provided FACTS.
        
        CRITICAL RULES (DO NOT VIOLATE):
        1.  **GAME CONTRACTS:**
            -   **Notrump:** 3NT, 4NT, 5NT
            -   **Majors (H/S):** 4H, 4S, 5H, 5S
            -   **Minors (C/D):** 5C, 5D (NOTE: 4C and 4D are PART SCORES, not Game)
        2.  **SCORING:** Do not hallucinate scores. A made contract of 4D is a part-score.
        3.  **DATA:** Do not calculate HCP yourself. Use the 'stats' provided in the JSON below.
        
        CONTEXT DATA:
        {json.dumps(context_payload, indent=2)}

        TASK:
        Provide a structured analysis in JSON format with the following sections:

        1. VERDICT: One short phrase (e.g., "OPTIMAL CONTRACT", "MISSED GAME", "OVERBID", "PART-SCORE MADE").
        
        2. BASIC_ANALYSIS (For Casual Players):
           - Critique the auction and play using Standard American (SAYC) fundamentals.
           - Explicitly mention if the contract reached Game or stopped in Part-Score.
           - Focus on point counting and simple raises.
           
        3. ADVANCED_INSIGHT (For Ambitious Learners):
           - Is there a more sophisticated bid (Splinter, Cue Bid, 2/1)?
           - Is there a complex play technique (Squeeze, Endplay)?
           - If nothing advanced applies, output "None".
           
        4. LESSON_MODULE (Conditional):
           - If a specific mistake was made (e.g., failed to draw trumps, forgot negative double), create a mini-lesson.
           - Format: {{ "topic": "Name of Topic", "content": "Explanation..." }}
           - If no major lesson is needed, output null.

        OUTPUT JSON FORMAT:
        {{
            "verdict": "...",
            "basic_analysis": "...",
            "advanced_insight": "...",
            "lesson_module": {{ "topic": "...", "content": "..." }} (or null)
        }}
        """

        try:
            # Paid Tier is fast!
            time.sleep(0.5)

            # --- PRODUCTION MODEL ---
            response = self.client.models.generate_content(
                model='gemini-flash-latest', 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json'
                )
            )
            
            if response.text:
                return json.loads(response.text)
            else:
                return {"error": "Empty response from AI"}

        except Exception as e:
            logger.error(f"Gemini API Call failed: {e}")
            return {"error": str(e)}