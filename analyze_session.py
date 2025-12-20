import os
import json
import time
from pathlib import Path
from loguru import logger

# Import our modules
from src.core.lin_parser import BridgeParser
from src.core.ai_orchestrator import AIOrchestrator

# CONFIGURATION
INPUT_FOLDER = "data/session_raw"
OUTPUT_FOLDER = "data/session_results"

def main():
    # 1. Setup
    parser = BridgeParser()
    try:
        ai = AIOrchestrator()
    except Exception as e:
        logger.error(f"Could not start AI: {e}")
        return

    # Ensure output folder exists
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # 2. Get Files
    if not os.path.exists(INPUT_FOLDER):
        logger.error(f"Input folder not found: {INPUT_FOLDER}")
        return

    lin_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(".lin")]
    logger.info(f"Found {len(lin_files)} files to process.")

    # 3. Batch Loop
    for index, filename in enumerate(lin_files):
        
        # --- SKIP LOGIC START ---
        output_filename = filename.replace(".lin", ".json")
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        if os.path.exists(output_path):
            logger.info(f"Skipping {filename} (Report already exists)")
            continue
        # --- SKIP LOGIC END ---

        logger.info(f"Processing {index + 1}/{len(lin_files)}: {filename}")
        
        file_path = os.path.join(INPUT_FOLDER, filename)
        
        # A. PARSE (The Math)
        with open(file_path, 'r') as f:
            content = f.read()
        
        parsed_data = parser.parse_lin_content(filename, content)
        
        if "error" in parsed_data:
            logger.error(f"Skipping {filename} due to parse error: {parsed_data['error']}")
            continue

        # B. ANALYZE (The AI)
        analysis = ai.analyze_hand(parsed_data, parsed_data['hands'])
        
        if "error" in analysis:
            # If AI fails, log it but DO NOT SAVE. 
            # We let the loop fall through to the sleep timer so we don't hammer the server.
            logger.error(f"AI Failed for {filename}: {analysis['error']}")
            logger.warning("Skipping save so this hand can be retried later.")
        else:
            # C. COMBINE & SAVE (Only if successful)
            final_record = {
                "meta": {
                    "filename": filename,
                    "timestamp": time.ctime()
                },
                "facts": parsed_data,   
                "ai_analysis": analysis 
            }
            
            with open(output_path, 'w') as f:
                json.dump(final_record, f, indent=2)
                
            logger.success(f"Saved report to: {output_path}")

        # D. RATE LIMIT PAUSE (Runs every time, even after error)
        logger.info("Waiting 10s for API rate limit...")
        time.sleep(10)

    logger.success("BATCH PROCESSING COMPLETE!")

if __name__ == "__main__":
    main()
