"""
01-hello-claude/app.py
════════════════════════════════════════════════════════════════════════════════
THE FIRST APP: Hello, Claude

What this does:
  Sends a message to Claude and prints the response. That's it.
  But every single line is explained, because understanding this one file
  means you understand the foundation every future app is built on.

Run it:
  cd cc-sandbox
  source venv/bin/activate
  python 01-hello-claude/app.py

What to watch:
  - The terminal will pause for a second (Claude is thinking)
  - Then you'll see a response appear
  - At the bottom: token counts. These tell you how much text went in and out.
════════════════════════════════════════════════════════════════════════════════
"""

# ── Imports ───────────────────────────────────────────────────────────────────
#
# sys.path.insert lets us import from the `shared` folder even though we're
# running from inside the `01-hello-claude` subfolder. Without this, Python
# wouldn't know where to find `shared/claude_client.py`.
#
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Now we can import our shared client (see shared/claude_client.py)
from shared.claude_client import client, MODEL
from shared.helpers import print_header, print_response


# ── The system prompt ─────────────────────────────────────────────────────────
#
# A "system prompt" is a set of instructions you give Claude BEFORE the
# conversation starts. It shapes how Claude behaves for every message in
# the session.
#
# Think of it like a job briefing: "Here's who you are, here's what you do."
# You don't repeat this every time — you set it once and Claude remembers it.
#
SYSTEM_PROMPT = """
You are a friendly assistant helping someone learn to build AI applications.

When you respond:
- Be concise and encouraging
- Use plain language (no jargon unless you explain it)
- If relevant, mention what concept the user just experienced
"""


# ── The user message ──────────────────────────────────────────────────────────
#
# This is what you (the "user") are sending to Claude. In a real app, this
# would come from a text box, a form, a file — anywhere. For now we hardcode
# it so we can focus on understanding the structure.
#
USER_MESSAGE = "Hello! I just ran my first agentic app. What did I just do?"


# ── Main function ─────────────────────────────────────────────────────────────
def main():
    print_header("App 01 — Hello, Claude")
    print(f"Model  : {MODEL}")
    print(f"Message: {USER_MESSAGE}")

    # ── The API call ──────────────────────────────────────────────────────────
    #
    # client.messages.create() is the core of everything.
    # Every app in this repo — simple or sophisticated — calls this same method.
    # The only difference is what you put inside it.
    #
    # Parameters explained:
    #
    #   model
    #     Which Claude model to use. We use claude-opus-4-6 — the most capable.
    #     The model is what you're "renting" thinking time from.
    #
    #   max_tokens
    #     The maximum length of Claude's response, measured in tokens.
    #     A token is roughly 0.75 words (so 1024 tokens ≈ 750 words).
    #     Claude will stop generating when it hits this limit.
    #     Setting this prevents runaway long responses (and runaway costs).
    #
    #   system
    #     The system prompt — sets Claude's role and behaviour.
    #     This goes BEFORE the conversation, not inside messages[].
    #
    #   messages
    #     The conversation so far, as a list of {role, content} dictionaries.
    #     role is always either "user" or "assistant".
    #     They must alternate. "user" always goes first.
    #
    print("\nSending message to Claude...")

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": USER_MESSAGE
            }
        ]
    )

    # ── Reading the response ──────────────────────────────────────────────────
    #
    # response is a Message object. Its most important parts:
    #
    #   response.content
    #     A list of content blocks. Usually just one: a text block.
    #     We take [0] (the first block) and then .text to get the string.
    #
    #   response.stop_reason
    #     Why Claude stopped generating. Common values:
    #       "end_turn"   — Claude finished naturally (what you want)
    #       "max_tokens" — Claude hit the limit you set (increase max_tokens)
    #       "tool_use"   — Claude wants to call a tool (later apps)
    #
    #   response.usage
    #     Token counts — how much text went in and out.
    #     input_tokens  = your system prompt + user message
    #     output_tokens = Claude's response
    #     This matters for understanding cost and context limits.
    #
    claude_reply = response.content[0].text

    print_response("Claude says:", claude_reply)

    # ── Token usage ───────────────────────────────────────────────────────────
    print(f"\nToken usage:")
    print(f"  Input  (your message + system prompt) : {response.usage.input_tokens}")
    print(f"  Output (Claude's response)            : {response.usage.output_tokens}")
    print(f"  Total                                 : {response.usage.input_tokens + response.usage.output_tokens}")
    print(f"\nStop reason: {response.stop_reason}")
    print("\nDone.")


# ── Entry point ───────────────────────────────────────────────────────────────
#
# `if __name__ == "__main__"` means: only run main() if this file is executed
# directly (e.g., `python app.py`). If another file imports this one, main()
# won't run automatically. This is a Python best practice.
#
if __name__ == "__main__":
    main()
