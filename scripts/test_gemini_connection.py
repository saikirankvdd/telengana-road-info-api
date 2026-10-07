import os
import sys
import logging
from dotenv import load_dotenv

# Suppress SDK standard warnings for cleaner test output
logging.getLogger("google.genai").setLevel(logging.ERROR)

def sanitize_output(text: str, secret: str) -> str:
    """Removes any instance of secret key from text output."""
    if secret and secret in text:
        return text.replace(secret, "[REDACTED_API_KEY]")
    return text

def run_gemini_connection_check():
    # 1. Load GEMINI_API_KEY from environment
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("GEMINI API CONNECTION FAILED")
        print("Diagnosis: Missing GEMINI_API_KEY environment variable in .env or environment.")
        sys.exit(1)

    # 2. Initialize official Gemini client
    try:
        from google import genai
    except ImportError:
        print("GEMINI API CONNECTION FAILED")
        print("Diagnosis: Missing dependency 'google-genai'. Please install using 'pip install google-genai'.")
        sys.exit(1)

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        safe_err = sanitize_output(str(e), api_key)
        print("GEMINI API CONNECTION FAILED")
        print(f"Error details: {safe_err}")
        print("Diagnosis: Client initialization failure.")
        sys.exit(1)

    # 3. Use an appropriate currently available Gemini Flash model
    models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-2.5-flash-lite"]
    last_error = None
    
    for model_name in models_to_try:
        try:
            # 4. Send a simple test request
            response = client.models.generate_content(
                model=model_name,
                contents="Ping test: Respond with 'OK'."
            )
            if response and response.text:
                # 5 & 6. Safe output, never print API key
                print("GEMINI API CONNECTION SUCCESSFUL")
                print(f"Model used: {model_name}")
                return
        except Exception as e:
            last_error = e
            continue

    # If all model requests failed
    safe_err = sanitize_output(str(last_error), api_key)
    print("GEMINI API CONNECTION FAILED")
    print(f"Error details: {safe_err}")
    
    err_msg = safe_err.lower()
    if "401" in err_msg or "invalid" in err_msg or "unauthorized" in err_msg or "api_key" in err_msg:
        print("Diagnosis: Invalid GEMINI_API_KEY or key authentication error.")
    elif "429" in err_msg or "quota" in err_msg or "rate limit" in err_msg or "resource_exhausted" in err_msg:
        print("Diagnosis: API Quota / Rate limit / Resource exhausted.")
    elif "404" in err_msg or "not found" in err_msg:
        print("Diagnosis: Specified Gemini model not found or deprecated.")
    else:
        print("Diagnosis: General API connection error. Check network connection or configuration.")

    sys.exit(1)

if __name__ == "__main__":
    run_gemini_connection_check()

