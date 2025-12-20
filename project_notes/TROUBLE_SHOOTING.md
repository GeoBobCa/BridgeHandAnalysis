Markdown

# Bridge Master Troubleshooting Guide

This document captures common errors encountered during development and their proven solutions.

## 1. AI / Gemini API Errors

### Error: `404 models/... is not found for API version v1beta`
**Symptoms:**
* The log shows an error referencing `v1beta`.
* The AI fails to analyze the hand.

**Cause:**
This indicates the application is running the **OLD** Google SDK (`google-generativeai`). Google deprecated the `v1beta` endpoint, and newer models (like Flash) require the new SDK (`v1`).

**Solution:**
1. Uninstall the old library and install the new one:
   ```bash
   uv pip uninstall google-generativeai
   uv pip install google-genai
Ensure src/core/ai_orchestrator.py imports the new library:

Python

# CORRECT
from google import genai
from google.genai import types

# INCORRECT
import google.generativeai as genai
Error: 429 RESOURCE_EXHAUSTED (Limit: 0)
Symptoms:

Error message: Quota exceeded for metric ... limit: 0, model: gemini-2.0-flash.

Cause: The specific model you selected (gemini-2.0-flash) is either restricted in your region or does not have a free tier available for your account type.

Solution: Switch to a stable, free-tier friendly model in src/core/ai_orchestrator.py:

Recommended: gemini-flash-latest or gemini-1.5-flash

Avoid: Experimental models (-exp) unless you have a paid billing account.

Error: ValueError: Missing GEMINI_API_KEY in .env
Symptoms:

The application crashes immediately upon analyzing a hand.

Log says: GEMINI_API_KEY not found.

Cause: The application cannot find the .env file, usually because the execution context (Working Directory) is different from the file location.

Solution:

Ensure the .env file is in the Project Root (same level as main.py).

Ensure the filename is exactly .env (not .env.txt).

The AIOrchestrator class must explicitly calculate the path:

Python

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
2. Environment & Execution Errors
Error: ModuleNotFoundError / Libraries missing
Symptoms:

You run the app and it complains about missing imports (google, loguru, etc.), even though you installed them.

Cause: You are likely running the script using the Global System Python instead of the Project Virtual Environment.

Solution:

Check VS Code: Ensure the bottom-right interpreter says ('.venv': venv).

Run Command: Always run the script using the python command, which forces the active environment:

PowerShell

# CORRECT
python .\main.py

# INCORRECT (Might use system python)
main.py
Debugging Tools
If you are unsure if the AI is connecting, create a temporary script debug_ai.py in the root:

Python

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
print("Models found:")
for m in client.models.list(config={'page_size': 10}):
    print(m.name)
Run it with python debug_ai.py to test connectivity independent of the GUI.