import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def get_groq_client():
    """
    Lazy initializer for the Groq API client.
    Ensures the client is created only once and reused.
    """
    if not hasattr(get_groq_client, "_client"):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError("❌ GROQ_API_KEY is not set in environment variables.")

        print("[groq_client] Initializing Groq client...")
        try:
            get_groq_client._client = Groq(api_key=api_key)
            print("[groq_client] ✅ Groq client ready.")
        except Exception as e:
            print(f"[groq_client] ⚠️ Failed to initialize Groq client: {e}")
            raise RuntimeError(f"Groq client initialization failed: {e}")

    return get_groq_client._client
