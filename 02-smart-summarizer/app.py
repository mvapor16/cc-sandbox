"""
02-smart-summarizer/app.py
════════════════════════════════════════════════════════════════════════════════
APP 02 — Smart Summarizer

What this does:
  You paste any text — an article, an email, a report, meeting notes.
  Claude reads it and returns a structured analysis: a summary, key points,
  the single most important takeaway, sentiment, and reading level.

New concepts introduced in this app (everything from App 01 still applies):

  1. PROMPT ENGINEERING
     In App 01 the system prompt was vague — "be friendly and helpful."
     Here it becomes a precise specification. We tell Claude EXACTLY what
     sections to return, in what order, with what headers. This is the
     difference between "can you summarise this?" and getting an answer you
     can rely on and build on.

  2. STRUCTURED OUTPUT (text-based)
     Claude's response isn't free-form prose — it's structured into labelled
     sections we can split and parse. This is the foundation of turning AI
     output into data your code can use. (App 03 takes this further with JSON.)

  3. INTERACTIVE INPUT
     Instead of a hardcoded message, the user types or pastes text at runtime.
     This makes the app genuinely useful, not just a demo.

  4. PARSING THE RESPONSE
     We split Claude's output by section headers and display each section
     separately. This is a pattern that scales all the way to production.

Run it:
  cd cc-sandbox
  python 02-smart-summarizer/app.py

Then paste any text when prompted and press Enter TWICE on a blank line when done.
════════════════════════════════════════════════════════════════════════════════
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.claude_client import client, MODEL
from shared.helpers import print_header, print_section, count_words


# ── The system prompt — the heart of this app ─────────────────────────────────
#
# PROMPT ENGINEERING is the practice of designing your instructions to Claude
# so precisely that you get reliable, structured, parseable output every time.
#
# Compare these two prompts:
#
#   Vague:   "Summarise this text for me."
#   → Claude might write a paragraph, a bullet list, or two sentences.
#     You never know what shape the output will be.
#
#   Precise: [what you see below]
#   → Claude returns exactly the sections listed, in the exact order,
#     with the exact headers. Your parsing code can depend on this.
#
# KEY TECHNIQUES USED HERE:
#
#   1. Role assignment ("You are a professional analyst...")
#      Framing Claude as an expert in a role measurably improves output quality.
#      It's not magic — it's telling Claude which "register" of knowledge to use.
#
#   2. Explicit output format with exact headers
#      "Use EXACTLY these headers" is not stylistic — our parse_sections()
#      function below splits on these strings. If Claude invents a new header,
#      the parse fails. So we enforce it in the prompt.
#
#   3. Negative constraints ("Do not add any text before ## SUMMARY")
#      Claude's default behaviour is to be conversational — "Great! Here's
#      my analysis...". Negative constraints suppress that so the output
#      starts exactly where we expect it to.
#
#   4. Slot-filling format with placeholders
#      Writing "[Positive / Neutral / Negative] — [one sentence why]" is clearer
#      than describing it in prose. Claude fills in the blanks.
#
SYSTEM_PROMPT = """
You are a professional analyst who produces crisp, high-signal summaries.

Your job is to read whatever text the user sends and return a structured analysis.

Return your analysis in EXACTLY this format, using these exact section headers:

## SUMMARY
[Write 2–3 sentences capturing the core idea and context of the text.]

## KEY POINTS
- [First key point — specific, not vague]
- [Second key point]
- [Continue for all significant points — aim for 3 to 6]

## TAKEAWAY
[The single most important sentence from this entire text. One sentence only.]

## SENTIMENT
[Positive / Neutral / Negative / Mixed] — [One sentence explaining why.]

## READING LEVEL
[Simple / Moderate / Technical] — [One sentence explaining why.]

Rules you must follow:
- Use EXACTLY the five headers shown above — no additions, no changes
- Do not write anything before ## SUMMARY (no greeting, no preamble)
- Do not write anything after the ## READING LEVEL section
- Bullet points use a dash (-), not numbers or symbols
- Be specific and direct — cut filler words
"""


# ── Getting input from the user ────────────────────────────────────────────────
#
# This is the first app where we take real input from the person running it.
# `input()` pauses the program and waits for the user to type or paste.
#
# For multi-line text (articles, reports), we read lines in a loop and stop
# when we see a blank line. This is a common CLI pattern for "end of input."
#
def get_text_from_user() -> str:
    """
    Collect multi-line text from the terminal.

    Reads lines until the user presses Enter TWICE in a row (two
    consecutive blank lines). A single blank line is treated as a
    paragraph break and preserved in the text, so you can paste
    multi-paragraph articles without accidentally cutting them off.

    Also handles Ctrl+D (EOF signal on Mac/Linux) for users who
    prefer that flow.

    Returns the full text as a single string, or exits cleanly if
    the user submits nothing.
    """
    print("\nPaste or type the text you want to analyse.")
    print("Press Enter TWICE on a blank line when you're done.")
    print("─" * 60)

    lines = []
    consecutive_blanks = 0
    while True:
        try:
            line = input()
            if line == "":
                if not lines:
                    continue              # Ignore leading blank lines
                consecutive_blanks += 1
                if consecutive_blanks >= 2:
                    break                 # Two blank lines = done
                lines.append(line)        # One blank line = paragraph break, keep it
            else:
                consecutive_blanks = 0
                lines.append(line)
        except EOFError:
            # Ctrl+D — treat as end of input
            break

    text = "\n".join(lines).strip()

    if not text:
        print("\nNo text received. Please try again with some content.")
        sys.exit(0)

    if len(text.split()) < 20:
        print(f"\nText is very short ({count_words(text)} words). Claude will")
        print("still analyse it, but results are richer with longer content.")

    return text


# ── Parsing the structured response ───────────────────────────────────────────
#
# Claude returns text like this:
#
#   ## SUMMARY
#   The text discusses...
#
#   ## KEY POINTS
#   - First point
#   - Second point
#
#   ## TAKEAWAY
#   ...
#
# We split on the "## " marker to extract each section into a dict:
#   {"SUMMARY": "The text discusses...", "KEY POINTS": "- First\n- Second", ...}
#
# This dict is then used by display_analysis() to print each section cleanly.
#
# WHY THIS MATTERS:
#   Parsing structured text output is the bridge between "Claude wrote some
#   words" and "my program has usable data." Even in production apps, you'll
#   often parse Claude's text responses before storing or displaying them.
#   App 03 introduces JSON output, which is stricter — but text-based
#   structured output like this is simpler and often sufficient.
#
def parse_sections(response_text: str) -> dict:
    """
    Split Claude's structured response into a dictionary of sections.

    Args:
        response_text: The full text of Claude's response

    Returns:
        A dict like {"SUMMARY": "...", "KEY POINTS": "...", ...}
        If a section is missing (Claude went off-script), it won't be in the dict.
    """
    sections = {}
    current_key = None
    current_lines = []

    for line in response_text.strip().split("\n"):
        if line.startswith("## "):
            # Save the previous section before starting the new one
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = line[3:].strip()   # e.g. "## SUMMARY" → "SUMMARY"
            current_lines = []
        else:
            current_lines.append(line)

    # Don't forget the last section (no "## " comes after it to trigger a save)
    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


# ── Displaying the analysis ────────────────────────────────────────────────────
def display_analysis(sections: dict, word_count: int, usage) -> None:
    """
    Print each parsed section with clean formatting.

    The order here matches the order Claude was instructed to produce them,
    so what you see on screen flows logically from summary → detail → meta.
    """
    print(f"\n  Input text: {word_count} words")

    # Define display order and friendly labels
    display_order = [
        ("SUMMARY",       "Summary"),
        ("KEY POINTS",    "Key Points"),
        ("TAKEAWAY",      "Takeaway"),
        ("SENTIMENT",     "Sentiment"),
        ("READING LEVEL", "Reading Level"),
    ]

    for section_key, display_label in display_order:
        content = sections.get(section_key)
        if content:
            print_section(display_label, content)
        else:
            # Claude didn't return this section — flag it so we can investigate
            print(f"\n  [{display_label}: not returned by Claude]")

    # Token usage — same as App 01, but notice input_tokens are now much larger
    # because the full text you pasted is sent to Claude as part of the message
    print("\n" + "─" * 60)
    print(f"  Token usage — input: {usage.input_tokens}  "
          f"output: {usage.output_tokens}  "
          f"total: {usage.input_tokens + usage.output_tokens}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print_header("App 02 — Smart Summarizer")
    print(f"  Model: {MODEL}")
    print("\n  Paste any text — an article, email, report, or meeting notes.")
    print("  Claude will return a structured analysis with five sections.")

    # Step 1: Get the text to summarise
    user_text = get_text_from_user()

    # Step 2: Build the messages list
    #
    # In App 01 we sent one message: the user's question.
    # Here the user's message is their pasted text — we explicitly ask
    # Claude to analyse it. The system prompt does the heavy lifting of
    # specifying the output format.
    #
    messages = [
        {
            "role": "user",
            "content": f"Please analyse this text:\n\n{user_text}"
        }
    ]

    print("\nAnalysing... ", end="", flush=True)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages
    )

    print("done.\n")

    # Step 3: Parse the structured response
    raw_text = response.content[0].text
    sections = parse_sections(raw_text)

    # Step 4: Display
    print_header("Analysis")
    display_analysis(sections, count_words(user_text), response.usage)
    print("\nDone.")


if __name__ == "__main__":
    main()
