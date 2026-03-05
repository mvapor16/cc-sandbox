"""
shared/claude_client.py
────────────────────────
The single place in this entire repo where we configure the Anthropic client.

Why centralise it here?
  - Every app imports from here instead of re-creating the client
  - If you ever change your key, model, or settings, you change it in one place
  - It also catches common setup mistakes (missing .env, missing key) early
    with a clear error message instead of a cryptic API error later

Usage in any app:
    from shared.claude_client import client, MODEL
    response = client.messages.create(model=MODEL, ...)
"""

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# ── Load the .env file ────────────────────────────────────────────────────────
#
# dotenv looks for a file called .env and loads its contents as environment
# variables. We tell it explicitly to look in the repo root (two levels up
# from this file) so it works no matter which subfolder you run from.
#
repo_root = Path(__file__).parent.parent   # /cc-sandbox/
load_dotenv(repo_root / ".env")

# ── Validate the key exists ───────────────────────────────────────────────────
api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    raise EnvironmentError(
        "\n\n"
        "  ANTHROPIC_API_KEY not found.\n\n"
        "  To fix this:\n"
        "    1. Create a file called .env in the root of the cc-sandbox folder\n"
        "    2. Add this line to it:  ANTHROPIC_API_KEY=sk-ant-your-key-here\n"
        "    3. Get your key from: https://console.anthropic.com\n"
    )

# ── The model we use across all apps ─────────────────────────────────────────
#
# claude-opus-4-6 is Anthropic's most capable model. We use it everywhere
# so you see what's possible. In production you'd sometimes swap to a faster,
# cheaper model for simple tasks — but for learning, always use the best.
#
MODEL = "claude-opus-4-6"

# ── Create the client ─────────────────────────────────────────────────────────
#
# anthropic.Anthropic() is the main entry point to the SDK.
# By passing api_key explicitly we make it crystal clear where the key comes
# from (your .env file), rather than relying on implicit environment lookup.
#
client = anthropic.Anthropic(api_key=api_key)
