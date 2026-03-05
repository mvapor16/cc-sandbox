"""
06-chat-with-memory/app.py
════════════════════════════════════════════════════════════════════════════════
APP 06 — Chat with Memory

What this does:
  A terminal chatbot that remembers everything you've said. Refer back to
  topics from ten messages ago — Claude will recall them. The conversation
  grows richer the longer it runs.

New concepts introduced in this app:

  1. CONVERSATION HISTORY
     Claude has no memory between API calls. Every call is stateless —
     Claude starts fresh each time.

     You create "memory" by maintaining the messages array yourself and
     sending the ENTIRE conversation history on every API call.

     This is how every AI chat product works — Claude.ai, ChatGPT, Gemini.
     They all store the conversation and replay it on every turn.

     The messages array alternates strictly: user → assistant → user → ...
     Claude cannot process two consecutive user messages without an assistant
     message in between.

  2. CONTEXT WINDOW GROWTH
     Every turn makes the messages array longer. After 20 exchanges, you're
     sending 40 messages of text on every API call. This has two consequences:

       Cost:    input token count grows with every turn (you pay for all of it)
       Limits:  eventually the conversation exceeds the context window (~200k tokens)

     App 06 tracks this live — watch the token count after each message.
     For most conversations this isn't a problem. But knowing it exists
     matters when building production systems (see App 17 for RAG solutions).

  3. WHAT "MEMORY" ACTUALLY MEANS
     Claude doesn't "remember" in the way humans do. It re-reads the entire
     conversation transcript on every call. The impression of memory is
     created by injecting history — Claude is seeing it fresh every time,
     same as you reading a chat log from the top.

     This distinction matters for:
       Privacy: the whole history is re-sent to the API every turn
       Cost:    you're billed for every token in history, every turn
       Editing: you can manipulate history (delete messages, change content)
                and Claude will behave as if that history is real

  4. COMMANDS AS A UX PATTERN
     Production chatbots need meta-controls beyond chat messages.
     App 06 introduces the /command pattern:
       /clear    → wipe history and start fresh
       /history  → show the full conversation transcript
       /save     → export the conversation to a text file
       /tokens   → show current context usage

Run it:
  python 06-chat-with-memory/app.py
════════════════════════════════════════════════════════════════════════════════
"""

import sys
import textwrap
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.claude_client import client, MODEL
from shared.helpers import print_header


# ── Persona ────────────────────────────────────────────────────────────────────
#
# The system prompt establishes Claude's personality for this chat session.
# It persists across the whole conversation — unlike messages, it doesn't
# consume context window space from the alternating turns.
#
SYSTEM_PROMPT = """You are a sharp, thoughtful assistant with excellent recall.

You remember everything from this conversation. When the user references
something they mentioned earlier — a name, a project, a preference — refer
back to it naturally without making a big deal of it.

Be concise but complete. Use plain language. Ask follow-up questions when
it would genuinely help you give a better answer.

If the user asks you to remember something specific, acknowledge it and use
it in your later responses."""


HELP_TEXT = """
  Commands:
  ─────────────────────────────────────────
  /help      Show this help
  /clear     Start a fresh conversation
  /history   Show the full conversation so far
  /save      Save the conversation to a text file
  /tokens    Show token usage for this session
  /quit      Exit
  ─────────────────────────────────────────
  Tip: Claude remembers everything in this session.
       Try referring back to things you said earlier."""


# ── Core chat function ─────────────────────────────────────────────────────────

def send_message(messages: list, user_text: str) -> tuple[str, object]:
    """
    Add a user message to history and get Claude's response.

    The entire messages array is sent every time. This is what creates
    the illusion of memory — Claude re-reads the full conversation on
    every single call.

    Returns (response_text, usage_object).
    """
    # Append the new user turn
    messages.append({"role": "user", "content": user_text})

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=messages   # ← the full history, every time
    )

    assistant_text = response.content[0].text

    # Append Claude's response so it's in history for the next turn
    messages.append({"role": "assistant", "content": assistant_text})

    return assistant_text, response.usage


# ── Display helpers ────────────────────────────────────────────────────────────

def print_claude(text: str) -> None:
    """Print Claude's response with consistent indentation and wrapping."""
    print()
    print("  Claude")
    print("  " + "─" * 6)
    for line in text.split("\n"):
        if not line.strip():
            print()
            continue
        # Wrap long lines at 72 chars, indented by 2 spaces
        wrapped = textwrap.fill(line.strip(), width=72, initial_indent="  ", subsequent_indent="  ")
        print(wrapped)
    print()


def show_history(messages: list) -> None:
    """Print the conversation history in a readable format."""
    if not messages:
        print("\n  No conversation yet.")
        return

    turns = len(messages) // 2
    print(f"\n  ── Conversation History ({turns} turn{'s' if turns != 1 else ''}) ──\n")

    for msg in messages:
        role_label = "  You" if msg["role"] == "user" else "  Claude"
        content = msg["content"]

        # Truncate very long messages in the history view
        if len(content) > 400:
            content = content[:400] + "  [...]"

        print(f"{role_label}:")
        for line in content.split("\n"):
            print(f"    {line.strip()}")
        print()

    print("  ── End of history ──")


def show_tokens(messages: list, session_input: int, session_output: int) -> None:
    """Show current context size and session token totals."""
    # Rough estimate: ~4 chars per token
    estimated_context_tokens = sum(len(m["content"]) for m in messages) // 4
    session_total = session_input + session_output

    print(f"""
  Token usage this session:
  ─────────────────────────────────────────
  Messages in history:   {len(messages)} ({len(messages) // 2} turns)
  Estimated context:     ~{estimated_context_tokens:,} tokens
  Session input tokens:  {session_input:,}
  Session output tokens: {session_output:,}
  Session total:         {session_total:,}
  ─────────────────────────────────────────
  Note: input tokens grow with every turn because the full
  conversation history is re-sent on every API call.""")


def save_conversation(messages: list) -> None:
    """Save the conversation to a timestamped .txt file."""
    if not messages:
        print("\n  Nothing to save — conversation is empty.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chat_{timestamp}.txt"

    lines = [
        f"Chat with Claude — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Model: {MODEL}",
        "=" * 60,
        ""
    ]
    for msg in messages:
        label = "You" if msg["role"] == "user" else "Claude"
        lines.append(f"[{label}]")
        lines.append(msg["content"])
        lines.append("")

    Path(filename).write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Saved to: {filename}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print_header("App 06 — Chat with Memory")
    print(f"  Model: {MODEL}")
    print("\n  Claude remembers everything in this conversation.")
    print("  Each turn builds on everything said before.")
    print(HELP_TEXT)

    # The conversation history. This list is THE memory.
    # Everything Claude "knows" about this conversation lives here.
    messages = []

    # Token tracking for /tokens command
    session_input_tokens  = 0
    session_output_tokens = 0

    while True:
        # ── Input ──────────────────────────────────────────────────────────
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        # ── Commands ───────────────────────────────────────────────────────
        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]

            if cmd == "/quit":
                print("\nGoodbye!")
                break

            elif cmd == "/help":
                print(HELP_TEXT)

            elif cmd == "/clear":
                messages = []
                session_input_tokens  = 0
                session_output_tokens = 0
                print("\n  Conversation cleared. Starting fresh.\n")

            elif cmd == "/history":
                show_history(messages)

            elif cmd == "/save":
                save_conversation(messages)

            elif cmd == "/tokens":
                show_tokens(messages, session_input_tokens, session_output_tokens)

            else:
                print(f"\n  Unknown command: {user_input}  (type /help for commands)\n")

            continue

        # ── Send to Claude ─────────────────────────────────────────────────
        try:
            response_text, usage = send_message(messages, user_input)

            session_input_tokens  += usage.input_tokens
            session_output_tokens += usage.output_tokens

            print_claude(response_text)

            # Status line: turn number and token cost of this call
            turn_number = len(messages) // 2
            print(f"  ── turn {turn_number}  "
                  f"in: {usage.input_tokens:,}  out: {usage.output_tokens:,}  "
                  f"session: {session_input_tokens + session_output_tokens:,} tokens\n")

        except Exception as e:
            print(f"\n  Error: {e}\n")
            # Roll back the user message we just appended so history stays consistent
            if messages and messages[-1]["role"] == "user":
                messages.pop()


if __name__ == "__main__":
    main()
