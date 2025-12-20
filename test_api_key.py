from google import genai
from google.genai import types
import sys

# --- PASTE YOUR KEY HERE ---
API_KEY = "AIzaSyD-UVSFRoSa1v3VSj5VGavEPjGYg0Vd5oI"


def stress_test_billing():
    print("--- STARTING BILLING STRESS TEST (New SDK) ---")
    print("Target: 20 rapid requests (Free Tier usually fails around #15)")

    # 1. Initialize the Client
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        print(f"❌ ERROR: Could not initialize client. {e}")
        return

    success_count = 0
    fail_count = 0

    # 2. Loop 20 times rapidly
    for i in range(1, 21):
        try:
            sys.stdout.write(f"Request {i}/20... ")
            sys.stdout.flush()

            # The new SDK syntax
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents="Say 'test'",
                config=types.GenerateContentConfig(
                    max_output_tokens=5
                )
            )

            print("✅ OK")
            success_count += 1

        except Exception as e:
            print("❌ FAILED")
            fail_count += 1
            error_msg = str(e)

            # 429 is the standard code for "Too Many Requests"
            if "429" in error_msg or "Resource exhausted" in error_msg:
                print(f"\n[!] HIT RATE LIMIT: You are likely still on the FREE TIER.")
                print("    (The billing link might need 5-10 mins to propagate.)")
                break
            elif "INVALID_ARGUMENT" in error_msg or "API_KEY_INVALID" in error_msg:
                print("\n[!] INVALID KEY: Check your API Key string.")
                break
            else:
                print(f"    Error details: {error_msg}")

    print("\n--- RESULTS ---")
    if success_count == 20:
        print("🎉 SUCCESS: Passed 20/20 requests.")
        print("DIAGNOSIS: Your Billing is CONNECTED. You are on the Paid Tier.")
    else:
        print(f"DIAGNOSIS: Completed {success_count}/20.")

if __name__ == "__main__":
    stress_test_billing()