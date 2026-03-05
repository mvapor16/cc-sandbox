"""
09-learning-reviewer/app.py
════════════════════════════════════════════════════════════════════════════════
APP 09 — Learning Reviewer

What this does:
  Submit any content — a document, article, email draft, training module,
  or presentation outline — and get a structured quality review scored against
  a rubric. Claude scores each criterion 1–5 with specific rationale, quotes
  from your content, and an actionable improvement suggestion.

New concept introduced in this app:

  DOMAIN-SPECIFIC PROMPTING + EVALUATION
  ────────────────────────────────────────
  Apps 01–08 used Claude as a general assistant.
  App 09 turns Claude into a *domain expert* with a *specific evaluative lens*.

  The key shift: the system prompt doesn't just set a role ("you are a reviewer")
  — it gives Claude a precise rubric, a scoring guide, and behavioral instructions.
  This is called *domain-specific prompting*. The output changes dramatically.

  Compare:
    Generic:   "Review this document."
    → vague impressions, no structure, hard to act on

    Domain-specific: "Score this against 5 criteria (Clarity, Structure, ...)
                      using a 1-5 scale. Quote the text. Give one improvement."
    → precise, structured, directly actionable

  The rubric is built into the system prompt — different rubrics create
  different reviewer "personas" from the same base model.

  DYNAMIC SYSTEM PROMPTS
  ──────────────────────
  Previous apps had a fixed SYSTEM_PROMPT constant.
  App 09 builds the system prompt *at runtime* from the chosen rubric:

    def build_system_prompt(rubric_name: str, criteria: list[str]) -> str:
        criteria_block = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(criteria))
        return f"You are reviewing against the '{rubric_name}' rubric...\n{criteria_block}"

  This means any rubric — including user-defined ones — becomes a fully
  specialized reviewer with no code changes. The content shapes the prompt;
  the prompt shapes the output.

Built-in rubrics:
  1. Professional Writing
  2. Technical Documentation
  3. Learning Content (70-20-10 Aligned)  ← directly relevant to McKinsey L&D
  4. Presentation / Slide Deck Outline

Run it:
  python 09-learning-reviewer/app.py
════════════════════════════════════════════════════════════════════════════════
"""

import sys
import textwrap
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.claude_client import client, MODEL
from shared.helpers import get_user_input, print_header


# ── Built-in rubrics ───────────────────────────────────────────────────────────
#
# Each rubric is a name + list of criteria strings.
# The criteria become numbered items in the system prompt Claude reads.
# Adding a new rubric here instantly creates a new reviewer persona.
#
RUBRICS = {
    "1": {
        "name": "Professional Writing",
        "criteria": [
            "Clarity — Is the main point immediately obvious to the reader?",
            "Structure — Is the content logically organized with a clear flow?",
            "Conciseness — Is every sentence earning its place? No filler or padding?",
            "Tone — Is the voice appropriate for a professional audience?",
            "Evidence — Are claims backed with specifics, data, or concrete examples?",
        ],
    },
    "2": {
        "name": "Technical Documentation",
        "criteria": [
            "Accuracy — Are technical details correct and precise?",
            "Completeness — Are all necessary steps, parameters, or concepts covered?",
            "Clarity — Can a reader with appropriate background follow this without confusion?",
            "Examples — Are concrete examples provided to illustrate abstract concepts?",
            "Structure — Are headings, lists, and code blocks used to aid navigation?",
        ],
    },
    "3": {
        "name": "Learning Content (70-20-10 Aligned)",
        "criteria": [
            "70% Experiential — Does content tie directly to real work tasks, decisions, or scenarios?",
            "20% Social — Are there prompts for peer discussion, coaching, or collaborative practice?",
            "10% Formal — Is structured instruction focused, bounded, and clearly distinct from the rest?",
            "Application — Will learners know *specifically* what to do differently after engaging?",
            "Relevance — Is the content compelling and immediately applicable to the target audience?",
        ],
    },
    "4": {
        "name": "Presentation / Slide Deck Outline",
        "criteria": [
            "Opening — Does it hook the audience and set clear expectations for what follows?",
            "Core message — Is there one clear 'so what' the audience will walk away with?",
            "Narrative flow — Does the structure tell a logical story: situation, complication, resolution?",
            "Evidence — Is the narrative supported with data, examples, or case studies?",
            "Call to action — Does the closing drive a specific decision or next step?",
        ],
    },
}


# ── Output schema ──────────────────────────────────────────────────────────────

class CriterionScore(BaseModel):
    criterion: str
    score: int = Field(ge=1, le=5, description="Score from 1 (poor) to 5 (excellent)")
    rationale: str = Field(
        description="Why this score? Quote specific phrases from the content as evidence."
    )
    suggestion: str = Field(
        description="One concrete, actionable improvement for this criterion specifically."
    )


class ReviewResult(BaseModel):
    overall_score: float = Field(ge=1.0, le=5.0)
    verdict: str = Field(description="One sentence: the single most important judgment about this content.")
    criteria_scores: list[CriterionScore]
    top_strengths: list[str] = Field(description="2-3 things done especially well. Be specific.")
    priority_improvements: list[str] = Field(
        description="Top 2-3 changes that would most improve this content. Be specific and actionable."
    )


# ── Dynamic system prompt ──────────────────────────────────────────────────────

def build_system_prompt(rubric_name: str, criteria: list[str]) -> str:
    """
    Build a domain-specific system prompt from a rubric.

    The criteria list becomes the reviewer's evaluative lens.
    The same model, different prompt → a completely different expert.

    This is the key lesson of App 09: prompt engineering is persona engineering.
    Change the rubric, change the reviewer. No code changes required.
    """
    criteria_block = "\n".join(f"  {i + 1}. {c}" for i, c in enumerate(criteria))

    return f"""You are an expert content reviewer evaluating against the "{rubric_name}" rubric.

Rubric criteria:
{criteria_block}

Scoring guide:
  5 — Excellent: a strong example, clearly exceeds expectations
  4 — Good: meets expectations with only minor gaps
  3 — Adequate: some genuine strengths but noticeable weaknesses
  2 — Weak: significant gaps, needs substantial revision
  1 — Poor: fails to meet this criterion

Instructions:
- Be specific: quote actual phrases from the content to support your scores
- Suggestions must be actionable: tell the author *exactly* what to change, not just what's wrong
- Your overall_score should be the honest average of the criteria scores
- The verdict must be your single most important observation about this content"""


# ── Core function ──────────────────────────────────────────────────────────────

def review_content(content: str, rubric_name: str, criteria: list[str]) -> ReviewResult:
    """
    Send content to Claude with a domain-specific rubric and get a structured review.

    The system prompt changes based on the rubric — same API call pattern as
    App 01, but now the prompt is built dynamically from user input.
    """
    system_prompt = build_system_prompt(rubric_name, criteria)

    response = client.messages.parse(
        model=MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {"role": "user", "content": f"Please review this content:\n\n{content}"}
        ],
        output_format=ReviewResult,
    )
    return response.parsed_output


# ── Output formatting ──────────────────────────────────────────────────────────

def _score_bar(score: int, width: int = 5) -> str:
    """Visual bar for a 1–5 score. e.g. score=3 → '███░░'"""
    filled = "█" * score
    empty = "░" * (width - score)
    return filled + empty


def _stars(score: float) -> str:
    """Convert a float score to star display. e.g. 3.8 → '★★★★☆'"""
    rounded = round(score)
    return "★" * rounded + "☆" * (5 - rounded)


def format_review(result: ReviewResult, rubric_name: str) -> None:
    """Print the structured review in a clear, scannable terminal layout."""

    # Header
    print()
    print(f"  ┌─ {rubric_name} ─{'─' * max(0, 50 - len(rubric_name))}┐")
    print(f"  │  Overall: {_stars(result.overall_score)}  {result.overall_score:.1f}/5.0")
    print(f"  │")
    for line in textwrap.wrap(result.verdict, width=60):
        print(f"  │  {line}")
    print(f"  └{'─' * 57}┘")

    # Criterion-by-criterion scores
    print("\n  Criteria Scores:\n")
    for cs in result.criteria_scores:
        # Short name is the part before the dash
        short_name = cs.criterion.split("—")[0].split("(")[0].strip()
        bar = _score_bar(cs.score)
        print(f"    {short_name:<22}  {bar}  {cs.score}/5")

        # Rationale (wrapped)
        for line in textwrap.wrap(cs.rationale, width=66):
            print(f"      {line}")

        # Suggestion
        print(f"      ↳ {cs.suggestion}")
        print()

    # Strengths
    print("  Top Strengths:")
    for s in result.top_strengths:
        for i, line in enumerate(textwrap.wrap(s, width=68)):
            prefix = "    ✓ " if i == 0 else "      "
            print(f"{prefix}{line}")
    print()

    # Improvements
    print("  Priority Improvements:")
    for imp in result.priority_improvements:
        for i, line in enumerate(textwrap.wrap(imp, width=68)):
            prefix = "    ▸ " if i == 0 else "      "
            print(f"{prefix}{line}")
    print()


# ── Rubric selection ───────────────────────────────────────────────────────────

def select_rubric() -> tuple[str, list[str]]:
    """Prompt the user to pick a built-in rubric or enter custom criteria."""
    print("\n  Choose a rubric:")
    for key, rubric in RUBRICS.items():
        print(f"    {key}. {rubric['name']}")
    print(f"    5. Custom (define your own criteria)\n")

    while True:
        choice = get_user_input("Rubric (1-5)")

        if choice in RUBRICS:
            r = RUBRICS[choice]
            print(f"\n  Using: {r['name']}")
            return r["name"], r["criteria"]

        if choice == "5":
            return _get_custom_rubric()

        print("  Please enter 1, 2, 3, 4, or 5.")


def _get_custom_rubric() -> tuple[str, list[str]]:
    """Collect a user-defined rubric name and criteria list."""
    name = get_user_input("Rubric name")
    if not name:
        name = "Custom Rubric"

    print("\n  Enter criteria one per line. Blank line when done.")
    print("  Format: 'Name — What it measures'\n")

    criteria = []
    while True:
        line = get_user_input(f"  Criterion {len(criteria) + 1}")
        if not line:
            if len(criteria) >= 2:
                break
            print("  Enter at least 2 criteria.")
        else:
            criteria.append(line)

    return name, criteria


# ── Content input ──────────────────────────────────────────────────────────────

def get_content() -> str:
    """
    Collect multi-line content from the user or load from a file.

    Offers two input modes:
      - Paste: type/paste directly, end with END
      - File: provide a path to a .txt or .md file

    Having both modes teaches an important pattern: always give users an
    escape hatch. Not everyone wants to paste 2,000 words into a terminal.
    """
    print("\n  How would you like to provide the content?")
    print("    1. Paste it here")
    print("    2. Load from a file (.txt or .md)\n")

    mode = get_user_input("Choice (1 or 2)")

    if mode == "2":
        return _load_from_file()
    else:
        return _paste_content()


def _paste_content() -> str:
    """Read multi-line pasted input, ending on 'END' or Ctrl+D."""
    print("\n  Paste your content below. Type END on its own line when done.\n")
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


def _load_from_file() -> str:
    """Read content from a .txt or .md file path."""
    path_str = get_user_input("File path")
    path = Path(path_str.strip("'\""))

    if not path.exists():
        print(f"  File not found: {path}")
        return ""

    if path.suffix.lower() not in (".txt", ".md"):
        print("  Only .txt and .md files are supported for content review.")
        return ""

    return path.read_text(encoding="utf-8").strip()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print_header("App 09 — Learning Reviewer")
    print(f"  Model: {MODEL}")
    print("\n  Submit content for AI quality review against a rubric.")
    print("  Each criterion scored 1-5 with rationale and improvement suggestions.")
    print("  Type 'quit' at the prompt to exit.\n")

    while True:
        cmd = get_user_input("Press Enter to start a review (or 'quit' to exit)")

        if cmd.lower() in ("quit", "exit", "q"):
            print("\nGoodbye!")
            break

        rubric_name, criteria = select_rubric()
        content = get_content()

        if not content:
            print("  No content provided.\n")
            continue

        word_count = len(content.split())
        print(
            f"\n  Reviewing {word_count:,} words against '{rubric_name}'...",
            end="",
            flush=True,
        )

        try:
            result = review_content(content, rubric_name, criteria)
            print(" done.")
            format_review(result, rubric_name)
        except Exception as e:
            print(f"\n  Error: {e}")

        print()


if __name__ == "__main__":
    main()
