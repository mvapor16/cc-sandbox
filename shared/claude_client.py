"""
shared/claude_client.py
────────────────────────
The single place in this entire repo where we configure the Anthropic client.

WHY IT'S HERE:
  Every app imports from here. If your key changes, you update .env.
  If the base URL changes, you update .env. Nothing else needs to change.

MCKINSEY NOTE:
  McKinsey routes Claude through their internal AI gateway (QuantumBlack).
  This means two things are different from a standard Anthropic setup:

    1. ANTHROPIC_BASE_URL — traffic goes to McKinsey's gateway URL, not
       directly to api.anthropic.com. The gateway then forwards to Anthropic.

    2. ANTHROPIC_API_KEY — instead of the usual sk-ant-... key, you use a
       JWT token from McKinsey's auth system. This token EXPIRES (roughly
       every 30 minutes) and must be refreshed from your McKinsey portal.

HOW TO REFRESH YOUR TOKEN:
  Go to your McKinsey AI gateway portal and copy the new ANTHROPIC_API_KEY
  value into your .env file. No code changes needed.

USAGE IN ANY APP:
    from shared.claude_client import client, MODEL
    response = client.messages.create(model=MODEL, ...)
"""

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# ── Load the .env file ────────────────────────────────────────────────────────
# Looks for .env in the repo root, regardless of which subfolder you run from.
repo_root = Path(__file__).parent.parent
load_dotenv(repo_root / ".env")

# ── Read environment variables ────────────────────────────────────────────────
api_key  = os.getenv("ANTHROPIC_API_KEY")
base_url = os.getenv("ANTHROPIC_BASE_URL")   # Optional — only needed for gateways

# ── Validate ──────────────────────────────────────────────────────────────────
if not api_key:
    raise EnvironmentError(
        "\n\n"
        "  ANTHROPIC_API_KEY not found.\n\n"
        "  To fix this:\n"
        "    1. Create a file called .env in the root of the cc-sandbox folder\n"
        "    2. Add this line:  ANTHROPIC_API_KEY=your-key-here\n"
        "    3. McKinsey users: copy the token from your AI gateway portal\n"
        "       and also set: ANTHROPIC_BASE_URL=https://anthropic.prod.ai-gateway...\n"
    )

# ── The model ─────────────────────────────────────────────────────────────────
# claude-opus-4-6 is Anthropic's most capable model.
# McKinsey's gateway supports all standard Anthropic model IDs.
MODEL = "claude-opus-4-6"

# ── Build client kwargs ───────────────────────────────────────────────────────
#
# We only pass base_url if it's set. This keeps the client compatible with
# both direct Anthropic keys (no base_url) and gateway setups like McKinsey's.
#
client_kwargs = {"api_key": api_key}

if base_url:
    # The Anthropic SDK accepts a custom base_url so all requests go through
    # the gateway instead of directly to api.anthropic.com.
    # The SDK automatically appends /v1/messages etc. to this URL.
    client_kwargs["base_url"] = base_url

# ── Create the client ─────────────────────────────────────────────────────────
client = anthropic.Anthropic(**client_kwargs)
