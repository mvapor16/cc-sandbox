"""
08-excel-agent/app.py
════════════════════════════════════════════════════════════════════════════════
APP 08 — Excel Agent

What this does:
  Point it at a CSV or Excel file. Then ask questions in plain English:
  "Which region had the highest revenue last quarter?"
  "How many rows have missing values in the Status column?"
  "What's the average deal size for enterprise customers?"

  Claude reads the data and answers — no formulas, no SQL, no pivot tables.

New concept introduced in this app:

  CSV/EXCEL PARSING + SMART CONTEXT FORMATTING
  ─────────────────────────────────────────────
  Real-world data is tabular. DataFrames don't fit cleanly into a prompt
  the way text does. This app teaches the key technique for getting
  spreadsheet data into Claude's context window:

  1. SCHEMA FIRST — column names + data types + null counts
     Claude needs to know what columns exist before it can reason about them.

  2. SUMMARY STATISTICS — min, max, mean, std for numeric columns
     Often Claude can answer aggregate questions from stats alone,
     without needing to see every row.

  3. CATEGORICAL VALUE COUNTS — top values per text column
     "Which regions appear?" → answered from value_counts, not raw rows.

  4. FULL DATA OR SAMPLE — rows come last, truncated if the file is large
     Small files (≤ MAX_ROWS_FULL rows): send everything.
     Large files: send a head+tail sample, note how much wasn't shown.

  This layered approach means Claude gets the most useful information first,
  within a bounded token budget — even for large files.

  STATEFUL Q&A LOOP
  ─────────────────
  Like App 05, the data is embedded in the first message and reused for every
  follow-up question. The conversation history grows, but the data is only
  sent once. Follow-up questions are cheap.

Why this matters:
  Spreadsheets are everywhere — budgets, sales data, project trackers, HR
  records, survey results. Once you know how to load and format a DataFrame
  for Claude, you can build natural-language interfaces for any of them.

Dependencies:
  pip install pandas openpyxl
  (openpyxl is the engine that reads .xlsx files)

Run it:
  python 08-excel-agent/app.py
════════════════════════════════════════════════════════════════════════════════
"""

import sys
import textwrap
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.claude_client import client, MODEL
from shared.helpers import get_user_input, print_header, print_section


# ── Configuration ──────────────────────────────────────────────────────────────

# If the file has ≤ this many rows, send the complete dataset.
# Above this, send schema + stats + a head/tail sample instead.
MAX_ROWS_FULL = 200

# When sampling large files, include this many rows total (head + tail).
MAX_ROWS_SAMPLE = 30

# How many top values to show per categorical column in the summary.
TOP_VALUES_PER_CAT_COL = 6


# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a data analyst assistant. A spreadsheet has been loaded and summarized for you.

When answering questions:
- Be specific: use actual column names, values, and numbers from the data
- State what you can and cannot determine from the provided context
- For large files, note if the answer might differ across unseen rows
- Use precise numbers — round only when it aids readability
- If the user asks for a visualization, describe what it would show clearly in text

When the data is a sample, be honest: say "based on the sample shown" when appropriate."""


# ── Data loading ───────────────────────────────────────────────────────────────

def load_spreadsheet(path: str) -> tuple[pd.DataFrame, str]:
    """
    Load a CSV or Excel file into a pandas DataFrame.

    Returns the DataFrame and a format label ("CSV" or "Excel").

    pandas is the standard Python library for tabular data. It reads both
    formats automatically — you just need the right engine for Excel files
    (openpyxl, installed via requirements.txt).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = p.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(path)
        fmt = "CSV"
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(path)
        fmt = "Excel"
    else:
        raise ValueError(f"Unsupported format '{suffix}'. Use .csv, .xlsx, or .xls")

    return df, fmt


# ── Context formatting ─────────────────────────────────────────────────────────

def format_for_claude(df: pd.DataFrame, filename: str) -> str:
    """
    Convert a DataFrame into a rich text summary for Claude's context.

    This is the core technique of this app: rather than dumping raw CSV text,
    we build a structured description that gives Claude what it needs to answer
    questions about the data — within a bounded token budget.

    The layers (in order):
      1. Shape: rows and columns at a glance
      2. Column schema: name, dtype, null count
      3. Numeric stats: describe() output for all numeric columns
      4. Categorical breakdowns: top value_counts per text column
      5. Row data: full dataset (small) or head+tail sample (large)
    """
    sections = []

    # ── 1. Shape ───────────────────────────────────────────────────────────────
    sections.append(
        f"File: {filename}\n"
        f"Shape: {len(df):,} rows × {len(df.columns)} columns"
    )

    # ── 2. Column schema ───────────────────────────────────────────────────────
    col_lines = ["Columns:"]
    for col in df.columns:
        dtype = str(df[col].dtype)
        nulls = df[col].isna().sum()
        null_note = f"  ({nulls:,} nulls)" if nulls > 0 else ""
        col_lines.append(f"  {col!r} [{dtype}]{null_note}")
    sections.append("\n".join(col_lines))

    # ── 3. Numeric summary statistics ─────────────────────────────────────────
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        stats = df[numeric_cols].describe().round(2)
        sections.append("Numeric column statistics:\n" + stats.to_string())

    # ── 4. Categorical value counts ────────────────────────────────────────────
    cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    if cat_cols:
        cat_lines = ["Categorical columns (top values):"]
        for col in cat_cols[:8]:  # cap at 8 columns to control context size
            counts = df[col].value_counts(dropna=False).head(TOP_VALUES_PER_CAT_COL)
            pairs = ", ".join(f"{str(v)!r}×{n}" for v, n in counts.items())
            unique = df[col].nunique()
            cat_lines.append(f"  {col!r}: {pairs}  [{unique} unique values]")
        sections.append("\n".join(cat_lines))

    # ── 5. Row data ────────────────────────────────────────────────────────────
    if len(df) <= MAX_ROWS_FULL:
        row_text = f"Full dataset ({len(df):,} rows):\n{df.to_string(index=True)}"
    else:
        half = MAX_ROWS_SAMPLE // 2
        sample = pd.concat([df.head(half), df.tail(half)])
        hidden = len(df) - MAX_ROWS_SAMPLE
        row_text = (
            f"Sample rows (first {half} and last {half} of {len(df):,} total):\n"
            f"{sample.to_string(index=True)}\n\n"
            f"[{hidden:,} rows not shown — ask specific questions to explore them]"
        )
    sections.append(row_text)

    return "\n\n".join(sections)


# ── Q&A loop ───────────────────────────────────────────────────────────────────

def ask(data_context: str, question: str, history: list) -> tuple[str, object]:
    """
    Ask a question about the loaded data.

    First call: embeds the full data context at the top of the message.
    Follow-up calls: just adds the question — Claude already has the data
    in its conversation history from the first turn.

    This is the same pattern as App 05 (File Analyzer), applied to tabular data.
    """
    if not history:
        # First question — embed the full data summary
        user_content = (
            f"Here is the spreadsheet data:\n\n{data_context}"
            f"\n\n{'─' * 40}\n\nQuestion: {question}"
        )
    else:
        # Follow-up — data is already in history
        user_content = question

    history.append({"role": "user", "content": user_content})

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=history
    )

    answer = response.content[0].text
    history.append({"role": "assistant", "content": answer})
    return answer, response.usage


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print_header("App 08 — Excel Agent")
    print(f"  Model: {MODEL}")
    print("\n  Load a CSV or Excel file, then ask questions in plain English.")
    print("  Supports: .csv  .xlsx  .xls\n")

    while True:
        raw_path = get_user_input("File path (or 'quit')")

        if raw_path.lower() in ("quit", "exit", "q"):
            print("\nGoodbye!")
            break

        if not raw_path:
            continue

        # Strip quotes — some terminals add them when you drag-and-drop a file
        file_path = raw_path.strip("'\"")

        try:
            print("  Loading...", end="", flush=True)
            df, fmt = load_spreadsheet(file_path)
            filename = Path(file_path).name
            data_context = format_for_claude(df, filename)
            print(f" done.  ({fmt} · {len(df):,} rows · {len(df.columns)} columns)\n")
        except Exception as e:
            print(f"\n  Error: {e}\n")
            continue

        print(f"  Ready. Ask anything about '{filename}'.")
        print("  Commands: 'new' to load a different file · 'quit' to exit\n")

        history = []

        while True:
            question = get_user_input("Question")

            if question.lower() in ("quit", "exit", "q"):
                print("\nGoodbye!")
                return

            if question.lower() in ("new", "load", "change", "file"):
                print()
                break

            if not question:
                continue

            try:
                print("\n  Analyzing...", end="", flush=True)
                answer, usage = ask(data_context, question, history)
                print(" done.\n")
                print_section("Answer", answer)
                print(
                    f"\n  [tokens: {usage.input_tokens:,} in · "
                    f"{usage.output_tokens:,} out]\n"
                )
            except Exception as e:
                print(f"\n  Error: {e}\n")
                # Roll back the failed user message so history stays consistent
                if history and history[-1]["role"] == "user":
                    history.pop()


if __name__ == "__main__":
    main()
