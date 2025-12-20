import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Force output to print immediately (disable buffering)
sys.stdout.reconfigure(line_buffering=True)

print("STEP 1: Starting Diagnostic Script...")

try:
    # 1. Load Environment
    env_path = Path(__file__).resolve().parent / ".env"
    print(f"STEP 2: Looking for .env at: {env_path}")
    
    if env_path.exists():
        print("   -> File found.")
    else:
        print("   -> CRITICAL: .env file NOT found!")
        
    load_dotenv(dotenv_path=env_path)

    # 2. Check Key
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        masked_key = api_key[:4] + "..." + api_key[-4:]
        print(f"STEP 3: API Key loaded successfully: {masked_key}")
    else:
        print("STEP 3: CRITICAL - API Key is None or Empty.")
        sys.exit(1)

    # 3. Import SDK (Doing this late to see if import causes the crash)
    print("STEP 4: Importing Google GenAI SDK...")
    from google import genai
    print("   -> SDK Imported.")

    # 4. Connect
    print("STEP 5: Initializing Client...")
    client = genai.Client(api_key=api_key)
    print("   -> Client initialized.")

    # 5. List Models
    print("STEP 6: Requesting Model List from Google (Network Call)...")
    pager = client.models.list(config={'page_size': 50})
    
    print("\n--- RAW MODEL LIST FROM GOOGLE ---")
    count = 0
    for model in pager:
        count += 1
        # Print everything found to ensure we aren't filtering too aggressively
        print(f"FOUND: {model.name}")
    
    print(f"\nTotal models found: {count}")
    print("STEP 7: Diagnostic Finished.")

except Exception as e:
    print(f"\n!!! CRASH !!!")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {e}")