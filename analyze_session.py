import os
import json
from src.core.lin_parser import LINParser
from src.core.bridge_math import BridgeMath
from src.core.ai_orchestrator import AIOrchestrator
from src.core.bridge_solver import BridgeSolver  # <--- NEW IMPORT

# CONFIG
RAW_DATA_DIR = "data/session_raw"
RESULTS_DIR = "data/session_results"

def run_analysis():
    # Initialize Engines
    parser = LINParser()
    math_engine = BridgeMath()
    ai_engine = AIOrchestrator()
    solver = BridgeSolver() # <--- NEW ENGINE
    
    # Ensure output directory exists
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    files = [f for f in os.listdir(RAW_DATA_DIR) if f.endswith(".lin")]
    print(f"Found {len(files)} session files.")

    for filename in files:
        file_path = os.path.join(RAW_DATA_DIR, filename)
        
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
            
        # 1. Parse Data
        hand_data = parser.parse_single_hand(raw_content, filename)
        deal_id = hand_data.get('board', 'Unknown')
        
        # 2. Run Math (HCP, distribution)
        math_results = math_engine.calculate_stats(hand_data)
        
        # 3. Run Solver (Double Dummy) <--- NEW STEP
        dds_results = solver.solve(hand_data['hands'])
        print(f"Bridge Engine: Analyzed {deal_id} (DDS Completed)")

        # 4. AI Analysis (Now gets dds_results too)
        ai_analysis = ai_engine.analyze_hand(hand_data, math_results, dds_results)
        
        # 5. Save Results
        full_record = {
            "facts": hand_data,
            "math": math_results,
            "dds": dds_results,  # <--- SAVING TRUTH DATA
            "ai_analysis": ai_analysis,
            "timestamp": "2025-12-20"
        }
        
        output_filename = filename.replace(".lin", ".json")
        with open(os.path.join(RESULTS_DIR, output_filename), "w", encoding="utf-8") as out:
            json.dump(full_record, out, indent=2)
            
        print(f"✅ Saved analysis for {deal_id}")

if __name__ == "__main__":
    run_analysis()
