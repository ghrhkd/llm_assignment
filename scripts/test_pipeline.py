"""
Quick smoke test: checks that all modules can be imported and API keys work.

Usage:
    python scripts/test_pipeline.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os

def check(label, fn):
    try:
        fn()
        print(f"  ✅ {label}")
        return True
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        return False


print("=== AI Wardrobe Pipeline — Smoke Test ===\n")

print("1. Module imports")
check("openai", lambda: __import__("openai"))
check("gradio", lambda: __import__("gradio"))
check("PIL", lambda: __import__("PIL"))
check("replicate", lambda: __import__("replicate"))

print("\n2. Environment variables")
check("OPENAI_API_KEY set", lambda: assert_env("OPENAI_API_KEY"))
check("REPLICATE_API_TOKEN set", lambda: assert_env("REPLICATE_API_TOKEN"))

print("\n3. OpenAI connection (simple completion)")
def test_openai():
    from openai import OpenAI
    client = OpenAI()
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say 'ok' in one word."}],
        max_tokens=5,
    )
    assert r.choices[0].message.content.strip().lower() in ("ok", "okay", "ok.")

check("GPT-4o-mini responds", test_openai)

print("\n4. WardrobeManager init")
check("WardrobeManager", lambda: __import__("src.wardrobe.wardrobe_manager", fromlist=["WardrobeManager"]))

print("\n=== Done ===")


def assert_env(key):
    val = os.environ.get(key, "")
    if not val or val.startswith("xx"):
        raise ValueError(f"{key} not set or is placeholder")
