import os
from dotenv import load_dotenv
from openai import OpenAI

# โหลดค่าจาก .env เข้าสู่ process นี้ (ไม่ override env ที่มีอยู่)
load_dotenv()

openrouter_key = os.getenv("OPENROUTER_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")
openrouter_base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
openai_base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


def mask(key: str) -> str:
    return f"{key[:5]}...{key[-4:]}" if key and len(key) > 10 else key


def test_client(key: str, base_url: str, label: str, headers: dict | None = None) -> None:
    print(f"\nTesting {label}")
    try:
        client = OpenAI(api_key=key, base_url=base_url, default_headers=headers)
        client.models.list()
        print(f"Auth OK at {base_url}")
    except Exception as e:
        print(f"Auth failed: {e}")
        print("Possible causes: expired key, insufficient credit, or base URL/headers mismatch")


if openrouter_key:
    print(f"Found OPENROUTER_API_KEY: {mask(openrouter_key)}")
    headers = {
        "HTTP-Referer": os.getenv("OPENROUTER_REFERRER", "http://localhost"),
        "X-Title": os.getenv("OPENROUTER_APP_NAME", "Agentic Stock Dashboard"),
    }
    test_client(openrouter_key, openrouter_base, "OpenRouter", headers=headers)
else:
    print("OPENROUTER_API_KEY not found")

if openai_key:
    print(f"\nFound OPENAI_API_KEY: {mask(openai_key)}")
    test_client(openai_key, openai_base, "OpenAI")
else:
    print("\nOPENAI_API_KEY not found")

if not openrouter_key and not openai_key:
    print("\nNo API keys found (OPENROUTER_API_KEY or OPENAI_API_KEY).")
    print("Check .env location or ensure python-dotenv is installed and load_dotenv() is called.")
