import os
import json
import glob
import time
from pathlib import Path
from dotenv import load_dotenv

# Import our custom modules
from src.core.lin_parser import LINParser
from src.core.ai_orchestrator import AIOrchestrator

# CONFIGURATION
SESSION_DIR = "data/session_raw"
RESULTS_DIR = "data/session_results"

def main():
    # 1. Load Environment (API Keys)
    load_dotenv()
    
    # 2. Initialize the Engine
    try:
        parser = LINParser()
        orchestrator = AIOrchestrator()
        print("✅ System initialized: Parser & AI Ready.")
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        return

    # 3. Prepare Folders
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

    # 4. Find all .lin files
    lin_files = glob.glob(os.path.join(SESSION_DIR, "*.lin"))
    if not lin_files:
        print(f"⚠️ No .lin files found in {SESSION_DIR}")
        return

    print(f"📂 Found {len(lin_files)} files to process...")

    # 5. Process Loop
    for file_path in lin_files:
        filename = os.path.basename(file_path)
        board_name = Path(file_path).stem  # e.g., "Board 1"
        
        # Check if already done (Skipping logic)
        # NOTE: Since we changed the data format, you should manually delete 
        # the old JSON files in 'data/session_results' before running this!
        output_filename = f"{board_name.replace(' ', '_')}.json"
        output_path = os.path.join(RESULTS_DIR, output_filename)
        
        if os.path.exists(output_path):
            print(f"⏩ Skipping {board_name} (Already analyzed)")
            continue

        print(f"Bridge Engine: Analyzing {board_name}...")
        
        try:
            # Step A: Parse the LIN file into Data
            with open(file_path, 'r') as f:
                raw_lin = f.read()
                
            hand_data = parser.parse_single_hand(raw_lin, board_name)
            
            # Step B: AI Analysis (Audrey Grant + Red Team)
            # We pass empty math_results={} because the stats are already inside hand_data
            ai_result = orchestrator.analyze_hand(hand_data, math_results={})
            
            # Step C: Combine & Save
            final_output = {
                "facts": hand_data,
                "ai_analysis": ai_result,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_output, f, indent=2)
                
            print(f"✅ Saved analysis for {board_name}")
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")

    print("\n🎉 Session Analysis Complete!")

if __name__ == "__main__":
    main()
