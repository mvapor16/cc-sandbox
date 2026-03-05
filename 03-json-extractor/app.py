"""
03-json-extractor/app.py
════════════════════════════════════════════════════════════════════════════════
APP 03 — JSON Extractor

What this does:
  You paste any text — an article, email, report, or meeting notes.
  Claude extracts structured data and returns it as a validated Python
  object. You get real fields you can access with dot notation:
  data.title, data.entities[0].name, data.key_facts[2], etc.

New concepts introduced in this app (everything from Apps 01–02 still applies):

  1. STRUCTURED OUTPUT WITH PYDANTIC
     In App 02, we asked Claude to use specific text headers and then split
     the response string ourselves. It worked — but it was fragile. One
     unexpected header and the parse breaks.

     App 03 uses client.messages.parse() instead of client.messages.create().
     You pass a Pydantic model class as output_format, and the SDK:
       a) Sends Claude the schema as a constraint (not just instructions)
       b) Guarantees the response matches the schema
       c) Returns a validated Python object — not a string

     The result: zero parsing code. No split(), no regex, no KeyError.

  2. PYDANTIC MODELS
     Pydantic is a Python library for data validation using type annotations.
     You define what your data should look like as a class, and Pydantic
     ensures any data you create actually matches that shape.

     class Person(BaseModel):
         name: str
         age: int

     That's it. Pydantic rejects anything that doesn't fit — wrong types,
     missing fields, extra fields — at the moment the object is created.

  3. MACHINE-READABLE VS HUMAN-READABLE OUTPUT
     App 02 produced nicely formatted text for a human to read.
     App 03 produces structured data for code to use.

     The difference matters: if you wanted to build a spreadsheet from
     100 articles, App 02 output would require parsing. App 03 output
     is already a Python object — just loop through it.

     This app displays both: human-readable formatting AND the raw JSON,
     so you can see exactly what's being produced under the hood.

Run it:
  cd cc-sandbox
  python 03-json-extractor/app.py

Then paste any text — extraction starts automatically when you stop pasting.
════════════════════════════════════════════════════════════════════════════════
"""

import json
import select
import sys
from pathlib import Path
from typing import List

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.claude_client import client, MODEL
from shared.helpers import count_words, print_header, print_section


# ── Pydantic models — the schema Claude must produce ──────────────────────────
#
# These classes are doing two jobs at once:
#
#   1. They define the SCHEMA — the shape of the data Claude will return.
#      The SDK reads these classes and tells Claude exactly what fields to fill.
#
#   2. They become the actual PYTHON OBJECTS you work with after the call.
#      Once the response comes back, `data.title` just works — no parsing.
#
# IMPORTANT: Every field needs a type annotation. Pydantic uses these to
# validate the response. If Claude returns an integer where you declared `str`,
# Pydantic will coerce it or raise an error, keeping your data clean.
#
class Entity(BaseModel):
    """A notable person, organisation, place, or concept from the text."""
    name: str          # The entity's name exactly as it appears in the text
    entity_type: str   # One of: person, organization, place, product, concept
    context: str       # One sentence describing their role or significance


class ExtractedData(BaseModel):
    """
    The full structured extraction result.

    This is the top-level object returned by client.messages.parse().
    Every field here will be filled by Claude, validated by Pydantic,
    and accessible as a normal Python attribute.
    """
    title: str               # A short descriptive title for this content (max 10 words)
    category: str            # Broadest topic: business, technology, politics, science,
                             #   health, culture, sport, or other
    one_line_summary: str    # The single most important sentence from the text
    entities: List[Entity]   # Key people, organisations, places, and concepts
    key_facts: List[str]     # 3–6 specific, concrete facts stated in the text
    dates_mentioned: List[str]  # Any dates, years, or time periods referenced
    sentiment: str           # Overall tone: positive, negative, neutral, or mixed


# ── System prompt ─────────────────────────────────────────────────────────────
#
# Notice how this prompt is shorter than App 02's. We don't need to specify
# headers or output format — the Pydantic schema handles all of that.
# The prompt only needs to describe the extraction task itself.
#
SYSTEM_PROMPT = """
You are a precise data extraction engine.

Your job: read the text the user provides and extract structured information
from it accurately and factually.

Rules:
- Extract only what is explicitly stated in the text
- Do not infer, assume, or add information not present
- For entities, include only those with a meaningful role in the text
- For key_facts, prefer specific claims over vague generalities
- For dates_mentioned, include years, specific dates, and relative time references
- If a field has no relevant content (e.g., no dates), return an empty list
"""


# ── Input: auto-detecting paste with a 500ms timeout ─────────────────────────
#
# Same technique as App 02: select.select() watches stdin with a short timeout.
# When you paste, all lines arrive in < 10 ms. A 500 ms silence = paste done.
#
def get_text_from_user() -> str:
    """
    Read pasted text from stdin. Analysis starts automatically 500ms after
    the paste completes — no keypress needed.
    """
    print("\nPaste your text — extraction starts automatically.")
    print("─" * 60)

    lines = []
    while True:
        timeout = 0.5 if lines else None
        ready = select.select([sys.stdin], [], [], timeout)[0]

        if not ready:
            break

        line = sys.stdin.readline()
        if line == "":    # Ctrl+D / EOF
            break
        lines.append(line.rstrip("\n"))

    text = "\n".join(lines).strip()

    if not text:
        print("\nNo text received. Exiting.")
        sys.exit(0)

    return text


# ── Display: human-readable rendering of the Pydantic object ─────────────────
#
# We deliberately show two views of the data:
#   1. A formatted, readable summary (like App 02 produced)
#   2. The raw JSON — so you can see what's actually in the object
#
# The contrast makes the point: you get BOTH human-friendly display AND
# machine-readable data, from the same Python object. No re-parsing needed.
#
def display_result(data: ExtractedData, word_count: int, usage) -> None:
    """
    Render the structured extraction result in two ways:
    formatted display (for humans) and raw JSON (for code).
    """
    print(f"\n  Input text: {word_count} words")

    # ── Formatted view ────────────────────────────────────────────────────────
    print_section("Title",   data.title)
    print_section("Category", data.category.capitalize())
    print_section("Summary",  data.one_line_summary)

    # Entities — each has three sub-fields, so we format them specially
    if data.entities:
        print(f"\n  Entities")
        print(f"  {'─' * 8}")
        for entity in data.entities:
            label = f"[{entity.entity_type}]"
            print(f"    {entity.name}  {label}")
            print(f"      {entity.context}")
    else:
        print("\n  Entities\n  ────────\n    None identified")

    # Key facts — a simple bulleted list
    if data.key_facts:
        print_section("Key Facts", "\n".join(f"- {f}" for f in data.key_facts))

    # Dates
    if data.dates_mentioned:
        print_section("Dates Mentioned", "\n".join(f"- {d}" for d in data.dates_mentioned))

    print_section("Sentiment", data.sentiment.capitalize())

    # ── Raw JSON view ─────────────────────────────────────────────────────────
    #
    # model_dump() is the Pydantic method that converts the object back to a
    # plain Python dict. json.dumps() then serialises it to a formatted string.
    #
    # This is the data your code would use programmatically — no further
    # parsing or processing needed. Pass it to a database, a spreadsheet,
    # an API, or another function directly.
    #
    print(f"\n  {'─' * 58}")
    print(f"  Raw JSON (what your code receives)")
    print(f"  {'─' * 58}")
    raw = json.dumps(data.model_dump(), indent=4)
    # Indent each line for consistent terminal alignment
    for line in raw.split("\n"):
        print(f"  {line}")

    # Token usage
    print(f"\n  {'─' * 58}")
    print(f"  Token usage — input: {usage.input_tokens}  "
          f"output: {usage.output_tokens}  "
          f"total: {usage.input_tokens + usage.output_tokens}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print_header("App 03 — JSON Extractor")
    print(f"  Model: {MODEL}")
    print("\n  Paste any text — Claude extracts structured data as validated JSON.")
    print("  Entities, facts, dates, sentiment — all as real Python fields.")

    # Step 1: Get the text to extract from
    user_text = get_text_from_user()

    # Step 2: Call client.messages.parse() instead of client.messages.create()
    #
    # THE KEY DIFFERENCE FROM APP 02:
    #
    #   App 02:  client.messages.create(...)
    #            → returns a Message; you read response.content[0].text (a string)
    #            → you then split that string on "## " to get sections
    #
    #   App 03:  client.messages.parse(output_format=ExtractedData, ...)
    #            → the SDK sends the Pydantic schema to Claude as a constraint
    #            → Claude's response is guaranteed to match the schema
    #            → the SDK validates and deserialises it into an ExtractedData object
    #            → you access response.parsed_output.title, .entities, etc.
    #
    # The schema is derived automatically from the Pydantic class. You don't
    # write any JSON Schema by hand — Pydantic generates it from the class.
    #
    print("\nExtracting... ", end="", flush=True)

    response = client.messages.parse(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Extract structured data from this text:\n\n{user_text}"
            }
        ],
        output_format=ExtractedData,   # ← the Pydantic class, not an instance
    )

    print("done.\n")

    # Step 3: Access the validated object
    #
    # response.parsed_output is already an ExtractedData instance.
    # No .text, no json.loads(), no splitting — just dot notation.
    #
    data: ExtractedData = response.parsed_output

    # Step 4: Display
    print_header("Extracted Data")
    display_result(data, count_words(user_text), response.usage)
    print("\nDone.")


if __name__ == "__main__":
    main()
