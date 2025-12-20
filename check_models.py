import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: No API Key found.")
else:
    client = genai.Client(api_key=api_key)
    print("\n--- YOUR AVAILABLE MODELS ---")
    try:
        for m in client.models.list(config={'page_size': 50}):
            # We only care about models that can generate text
            if "generateContent" in m.supported_actions:
                print(f"Model Name: {m.name}")
    except Exception as e:
        print(f"Error: {e}")