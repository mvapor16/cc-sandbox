"""
05-file-analyzer/app.py
════════════════════════════════════════════════════════════════════════════════
APP 05 — File Analyzer

What this does:
  You point it at any file on your computer — a .txt document, a .csv
  spreadsheet, a .json config, a .md README, or a .pdf report — and then
  ask questions about it in plain English. Claude reads the whole file and
  answers accurately, citing specific content.

New concepts introduced in this app:

  1. FILE I/O AND DOCUMENT INPUT
     Real-world AI applications rarely work on text you type manually.
     They work on documents, spreadsheets, logs, and reports. This app
     teaches the pattern: read a file → feed its content to Claude.

     Each file type requires different handling:
       .txt / .md  → read as plain text (straightforward)
       .csv        → parse rows/columns, give Claude a structured view
       .json       → parse and pretty-print so structure is visible
       .pdf        → extract text from each page using pypdf

  2. CONTEXT WINDOW AWARENESS
     Claude has a maximum context window (how much text it can hold in
     "working memory" at once). Very large files can exceed this limit.

     This app:
       - Estimates file size in tokens before sending
       - Warns if a file is very large
       - Truncates gracefully rather than crashing

     In production systems, this problem is solved with RAG (App 17).
     Here, we keep it simple: load the whole file if it fits.

  3. STATEFUL Q&A LOOP
     App 04 reset the conversation after every question. App 05 keeps
     the conversation history across multiple questions about the same file.

     This means Claude can answer follow-up questions like:
       "What was the average in the first column?" → answer
       "Now show me just the rows above that average" → uses prior context

     The file content is injected once (in the first message). Subsequent
     turns just add the new question — Claude already "has" the file.

  4. MULTI-TURN DOCUMENT ANALYSIS
     Combining file loading + conversation history creates a document
     analyst: you load a report or dataset and explore it conversationally,
     each question building on the last.

Run it:
  python 05-file-analyzer/app.py [optional: path/to/file]
════════════════════════════════════════════════════════════════════════════════
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.claude_client import client, MODEL
from shared.helpers import get_user_input, print_header, print_section


SYSTEM_PROMPT = """You are a precise document analyst. You have been given the full contents of a file.

When answering questions:
- Be specific — quote relevant sections, cite exact numbers, reference actual content
- For CSV/tabular data, refer to column names and row values directly
- For JSON data, reference exact key names and values
- If something is not in the file, say so clearly — never invent information
- Follow-up questions build on the same file — you don't need it repeated"""


# ── File loading ───────────────────────────────────────────────────────────────
#
# Each file type needs its own loading strategy. The goal is always the same:
# produce a clean text representation that Claude can reason about.
#
# Notice how CSV and JSON get special treatment — we don't just dump raw bytes,
# we structure the content so Claude can see columns, rows, and keys clearly.
#

def load_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_csv(path: Path) -> str:
    """
    Load a CSV file and return a readable representation.

    We include:
      - A header line showing column names
      - A separator line
      - All data rows
      - A summary at the top (row count, column count)

    This gives Claude a clear picture of the data's shape before the rows.
    """
    rows = []
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        return "Empty CSV file."

    headers = rows[0]
    data_rows = rows[1:]
    n_cols = len(headers)
    n_rows = len(data_rows)

    lines = [
        f"CSV file: {n_rows} data rows × {n_cols} columns",
        "",
        ",".join(headers),
        "─" * max(len(",".join(headers)), 40),
    ]
    for row in data_rows:
        lines.append(",".join(row))

    return "\n".join(lines)


def load_json(path: Path) -> str:
    """
    Load and pretty-print a JSON file.

    Pretty-printing (indent=2) makes the structure visible to Claude —
    it can see nesting, key names, and value types at a glance.
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(raw)
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
        # Rough structure summary at the top
        if isinstance(data, list):
            summary = f"JSON array with {len(data)} items"
        elif isinstance(data, dict):
            summary = f"JSON object with {len(data)} top-level keys: {', '.join(list(data.keys())[:8])}"
        else:
            summary = f"JSON value (type: {type(data).__name__})"
        return f"{summary}\n\n{pretty}"
    except json.JSONDecodeError as e:
        return f"File has .json extension but is not valid JSON: {e}\n\nRaw content:\n{raw}"


def load_pdf(path: Path) -> str:
    """
    Extract text from a PDF file page by page.

    pypdf is a pure-Python PDF reader. It handles text-based PDFs well
    but may struggle with scanned images (which require OCR, out of scope here).
    """
    try:
        import pypdf
    except ImportError:
        return (
            "PDF support requires the 'pypdf' package.\n"
            "Install it with:  pip install pypdf"
        )

    try:
        reader = pypdf.PdfReader(str(path))
        n_pages = len(reader.pages)
        pages = []
        for i, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"--- Page {i} of {n_pages} ---\n{text.strip()}")

        if not pages:
            return f"PDF has {n_pages} pages but no extractable text (may be a scanned image PDF)."

        return f"PDF file: {n_pages} pages\n\n" + "\n\n".join(pages)

    except Exception as e:
        return f"Could not read PDF: {e}"


def load_file(path: Path) -> tuple[str, str]:
    """
    Dispatch to the right loader based on file extension.
    Returns (content_string, file_type_label).
    """
    suffix = path.suffix.lower()

    loaders = {
        ".txt":  (load_txt,  "text"),
        ".md":   (load_txt,  "markdown"),
        ".csv":  (load_csv,  "CSV"),
        ".json": (load_json, "JSON"),
        ".pdf":  (load_pdf,  "PDF"),
    }

    if suffix in loaders:
        loader_fn, label = loaders[suffix]
        return loader_fn(path), label
    else:
        # Unknown extension — try reading as plain text anyway
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return content, f"{suffix} (read as text)"
        except Exception as e:
            return f"Could not read file: {e}", "unknown"


# ── Q&A with the file ──────────────────────────────────────────────────────────

def ask(file_content: str, file_name: str, question: str, history: list) -> tuple[str, object]:
    """
    Ask Claude a question about the loaded file.

    On the FIRST call (empty history), the file content is embedded in the
    user message so Claude can read it. On SUBSEQUENT calls, the file is
    already in the conversation history — we just add the new question.

    This is the key insight: you only need to send the file once.
    Every follow-up question is a short message; Claude already has the file.
    """
    if not history:
        # First question — include the full file content
        user_content = (
            f"Here is the file '{file_name}':\n\n"
            f"{file_content}\n\n"
            f"─────\n\n"
            f"Question: {question}"
        )
    else:
        # Follow-up — file is already in history
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


# ── File path input ────────────────────────────────────────────────────────────

def get_file_path() -> Path:
    """
    Prompt the user for a file path. Accepts drag-and-drop (which wraps
    paths in quotes on many terminals) and validates the file exists.
    """
    while True:
        raw = get_user_input("File path (drag & drop works, or type the path)")

        # Remove surrounding quotes that terminals add on drag & drop
        raw = raw.strip().strip("'\"")

        if not raw:
            print("  Please enter a path.")
            continue

        path = Path(raw).expanduser()

        if not path.exists():
            print(f"\n  Not found: {path}")
            print("  Check the path and try again.")
            continue

        if path.is_dir():
            print(f"\n  That's a folder, not a file. Please point to a specific file.")
            continue

        return path


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print_header("App 05 — File Analyzer")
    print(f"  Model: {MODEL}")
    print("\n  Load any file and ask questions about it in plain English.")
    print("  Supported formats: .txt  .md  .csv  .json  .pdf")
    print("  (Other formats are attempted as plain text.)\n")

    # ── Step 1: Get and load the file ──────────────────────────────────────
    # Accept file path as a command-line argument for convenience
    if len(sys.argv) > 1:
        file_path = Path(" ".join(sys.argv[1:])).expanduser()
        if not file_path.exists():
            print(f"  File not found: {file_path}")
            sys.exit(1)
    else:
        file_path = get_file_path()

    print(f"\n  Loading {file_path.name}...", end="", flush=True)
    content, file_type = load_file(file_path)
    word_count = len(content.split())
    char_count = len(content)
    print(f" done.")
    print(f"  Type: {file_type}  |  Words: {word_count:,}  |  Characters: {char_count:,}")

    # ── Step 2: Warn if file is very large ─────────────────────────────────
    #
    # Rough token estimate: ~4 characters per token. Claude's context window
    # is ~200k tokens. We warn at 100k tokens (~400k chars) and hard-truncate
    # at 150k tokens (~600k chars) to leave room for the conversation.
    #
    WARN_CHARS  = 400_000   # ~100k tokens — warn the user
    TRUNC_CHARS = 600_000   # ~150k tokens — hard truncate

    if char_count > TRUNC_CHARS:
        content = content[:TRUNC_CHARS]
        print(f"\n  Warning: File is very large. Truncated to ~150k tokens.")
        print("  For large files, consider using a RAG approach (App 17).")
    elif char_count > WARN_CHARS:
        print(f"\n  Note: Large file (~{word_count // 1000}k words). "
              f"Each question will use significant tokens.")

    # ── Step 3: Q&A loop ───────────────────────────────────────────────────
    print(f"\n  File loaded. Ask questions below.")
    print("  Type 'quit' to exit, 'new' to load a different file.\n")

    conversation_history = []

    while True:
        question = get_user_input("Your question")

        if question.lower() in ("quit", "exit", "q"):
            print("\nGoodbye!")
            break

        if question.lower() in ("new", "reload"):
            # Let the user load a different file without restarting
            print()
            file_path = get_file_path()
            print(f"\n  Loading {file_path.name}...", end="", flush=True)
            content, file_type = load_file(file_path)
            word_count = len(content.split())
            print(f" done. ({word_count:,} words, type: {file_type})")
            conversation_history = []
            print("  New file loaded. Conversation history cleared.\n")
            continue

        if not question:
            print("  Please enter a question.")
            continue

        print("\n  Thinking...", end="", flush=True)
        answer, usage = ask(content, file_path.name, question, conversation_history)
        print(" done.\n")

        print_section("Answer", answer)

        turns = len(conversation_history) // 2
        print(f"\n  Tokens this call: {usage.input_tokens:,} in / {usage.output_tokens:,} out"
              f"  |  Conversation turn: {turns}")
        print()


if __name__ == "__main__":
    main()
