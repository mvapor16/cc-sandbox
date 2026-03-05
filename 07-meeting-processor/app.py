"""
07-meeting-processor/app.py
════════════════════════════════════════════════════════════════════════════════
APP 07 — Meeting Processor

What this does:
  Paste raw meeting notes — any format, any length — and get back a structured
  analysis: participants, key decisions, action items with owners and priorities,
  open questions, and next steps. All in one API call.

New concept introduced in this app:

  NESTED PYDANTIC MODELS (multi-output formatting)
  ─────────────────────────────────────────────────
  App 03 introduced Pydantic for flat output (one level of fields).
  App 07 introduces *nested* models — objects that contain other objects.

  Real business output is rarely flat. A meeting produces:
    - A list of ActionItem objects (each with description, owner, deadline,
      and priority)
    - A list of Decision objects (description + rationale)
    - A list of strings (participants, open questions)
    - A single next_steps string

  With nested Pydantic models, you describe this entire structure once,
  and client.messages.parse() guarantees Claude returns exactly that shape —
  no parsing code, no validation logic, no defensive checks.

  The key pattern:

    class ActionItem(BaseModel):
        description: str
        owner: Optional[str] = None       # ← Optional fields get None if absent
        deadline: Optional[str] = None
        priority: str

    class MeetingAnalysis(BaseModel):
        summary: str
        participants: list[str]
        action_items: list[ActionItem]    # ← list of nested objects
        decisions: list[Decision]
        ...

  Claude fills in the entire tree. Python gets a fully typed, validated object.
  No parsing. No key errors. No surprises.

Why this matters:
  The same pattern — describe a rich output schema, call .parse() — works for
  any structured business output: resumes, contracts, customer feedback,
  sales calls, support tickets, incident reports. Once you see this pattern,
  you'll reach for it constantly.

Run it:
  python 07-meeting-processor/app.py
════════════════════════════════════════════════════════════════════════════════
"""

import sys
import textwrap
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.claude_client import client, MODEL
from shared.helpers import get_user_input, print_header, print_section


# ── Output schema ──────────────────────────────────────────────────────────────
#
# These three classes define the shape of Claude's response.
# Nesting ActionItem and Decision inside MeetingAnalysis means Claude must
# return a complete, typed object tree — not just a flat dict.
#

class ActionItem(BaseModel):
    description: str
    owner: Optional[str] = None     # person responsible; None if not mentioned
    deadline: Optional[str] = None  # exact text from notes, e.g. "EOD Friday"
    priority: str                   # "high", "medium", or "low"


class Decision(BaseModel):
    description: str
    rationale: Optional[str] = None  # why this decision was made, if stated


class MeetingAnalysis(BaseModel):
    summary: str                      # 2-3 sentence overview
    participants: list[str]           # everyone mentioned by name
    decisions: list[Decision]         # explicit decisions/agreements reached
    action_items: list[ActionItem]    # tasks with owner + deadline + priority
    open_questions: list[str]         # unresolved issues or follow-up needed
    next_steps: str                   # forward-looking closing summary


# ── Prompt ─────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a meticulous meeting analyst. Extract every meaningful detail.

From meeting notes, produce:
- summary: 2-3 sentences capturing what the meeting was about and the outcome
- participants: everyone mentioned by name (first name or full name, as written)
- decisions: explicit agreements or conclusions reached; include rationale if stated
- action_items: every task, commitment, or follow-up mentioned
    - owner: who is responsible (use "Unassigned" if not stated)
    - deadline: exact phrasing from the notes ("by Thursday", "next sprint"), or null
    - priority: "high" if urgent/blocking, "medium" if important, "low" otherwise
- open_questions: anything unresolved, unclear, or needing follow-up
- next_steps: a 1-2 sentence forward-looking summary of what happens next

Be thorough — it's better to capture too many action items than miss one.
If a name isn't clear, use whatever form appears in the notes."""


# ── Core function ──────────────────────────────────────────────────────────────

def process_meeting(notes: str) -> MeetingAnalysis:
    """
    Send meeting notes to Claude and get back a fully structured MeetingAnalysis.

    Uses client.messages.parse() — the same as App 03, but now with a nested
    schema. Claude must populate the entire object tree, not just a flat dict.
    """
    response = client.messages.parse(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Here are the meeting notes:\n\n{notes}"}],
        output_format=MeetingAnalysis,
    )
    return response.parsed_output


# ── Output formatting ──────────────────────────────────────────────────────────

PRIORITY_LABEL = {"high": "[HIGH]", "medium": "[MED] ", "low": "[LOW] "}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def format_analysis(analysis: MeetingAnalysis) -> None:
    """Print the structured analysis in a readable terminal layout."""

    print_section("Summary", analysis.summary)

    # Participants
    print("\n  Participants:")
    for name in analysis.participants:
        print(f"    • {name}")

    # Decisions
    if analysis.decisions:
        print("\n  Key Decisions:")
        for i, d in enumerate(analysis.decisions, 1):
            print(f"    {i}. {d.description}")
            if d.rationale:
                for line in textwrap.wrap(d.rationale, width=68):
                    print(f"       ↳ {line}")

    # Action items — sorted by priority
    if analysis.action_items:
        sorted_items = sorted(analysis.action_items, key=lambda x: PRIORITY_ORDER.get(x.priority, 1))
        print("\n  Action Items:")
        for item in sorted_items:
            tag = PRIORITY_LABEL.get(item.priority, "[MED] ")
            owner = item.owner or "Unassigned"
            deadline = f"  ·  due: {item.deadline}" if item.deadline else ""
            print(f"    {tag}  {item.description}")
            print(f"            → {owner}{deadline}")

    # Open questions
    if analysis.open_questions:
        print("\n  Open Questions:")
        for q in analysis.open_questions:
            print(f"    ?  {q}")

    print()
    print_section("Next Steps", analysis.next_steps)


# ── Input helpers ──────────────────────────────────────────────────────────────

def get_meeting_notes() -> str:
    """
    Collect multi-line meeting notes from the user.

    The user types or pastes their notes, then types END on its own line
    (or presses Ctrl+D) to signal they're done.

    This is a common terminal pattern for multi-line input: use a sentinel
    value rather than a timeout, so paste of any length works reliably.
    """
    print("\n  Paste your meeting notes below.")
    print("  Type END on its own line (or Ctrl+D) when done.\n")

    lines = []
    try:
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
    except EOFError:
        pass

    return "\n".join(lines).strip()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print_header("App 07 — Meeting Processor")
    print(f"  Model: {MODEL}")
    print("\n  Paste meeting notes → get action items, decisions, and summary.")
    print("  Type 'quit' at the prompt to exit.\n")

    while True:
        cmd = get_user_input("Press Enter to paste notes (or 'quit' to exit)")

        if cmd.lower() in ("quit", "exit", "q"):
            print("\nGoodbye!")
            break

        notes = get_meeting_notes()

        if not notes:
            print("  No notes provided.\n")
            continue

        word_count = len(notes.split())
        print(f"\n  Processing {word_count} words...", end="", flush=True)

        try:
            analysis = process_meeting(notes)
            print(" done.")
            format_analysis(analysis)
        except Exception as e:
            print(f"\n  Error: {e}")

        print()


if __name__ == "__main__":
    main()
