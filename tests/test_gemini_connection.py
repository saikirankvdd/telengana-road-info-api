import os
import pytest
from dotenv import load_dotenv

load_dotenv()

@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
def test_gemini_api_connection():
    from google import genai
    api_key = os.getenv("GEMINI_API_KEY")
    assert api_key, "GEMINI_API_KEY must be present"
    
    client = genai.Client(api_key=api_key)
    models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]
    
    last_error = None
    response = None
    
    for model in models_to_try:
        try:
            response = client.models.generate_content(
                model=model,
                contents="Ping test: Respond with 'OK'."
            )
            if response and response.text:
                break
        except Exception as e:
            last_error = e
            continue
            
    assert response is not None and response.text is not None, f"All Flash models failed: {last_error}"
    assert len(response.text) > 0
