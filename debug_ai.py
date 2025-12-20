import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# 1. Load the Environment
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")

print("-" * 40)
print(f"DEBUG TOOL: Checking Gemini Connection")
print(f"API Key found: {'Yes' if api_key else 'NO'}")
print("-" * 40)

if not api_key:
    print("CRITICAL: No API Key found in .env")
    exit()

try:
    # 2. Connect
    client = genai.Client(api_key=api_key)
    
    # 3. List Models
    print("Attempting to list available models...")
    print("(This checks if your Key and SDK are working)")
    
    # We ask for models that support 'generateContent'
    pager = client.models.list(config={'page_size': 50})
    
    found_flash = False
    print("\n--- AVAILABLE MODELS ---")
    for model in pager:
        # We only care about generation models, not embedding models
        if "generateContent" in model.supported_generation_methods:
            print(f" > {model.name}")
            if "flash" in model.name:
                found_flash = True

    print("-" * 40)
    if found_flash:
        print("SUCCESS: We found 'flash' models. The connection is good.")
    else:
        print("WARNING: Connected, but no 'flash' models found.")

except Exception as e:
    print("\nCONNECTION FAILED!")
    print(f"Error details: {e}")