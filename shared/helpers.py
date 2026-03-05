"""
shared/helpers.py
──────────────────
Small utility functions reused across multiple apps.

These are not Claude-specific — they're just common Python patterns
that come up repeatedly when building CLI tools and web apps.
"""

import sys
import textwrap


def print_header(title: str) -> None:
    """Print a visible section header in the terminal."""
    width = 60
    print("\n" + "─" * width)
    print(f"  {title}")
    print("─" * width)


def print_response(label: str, text: str, wrap_width: int = 70) -> None:
    """
    Print Claude's response with a label and light text wrapping.

    Args:
        label:      A short label like "Claude says:" printed above the text
        text:       The response text from Claude
        wrap_width: Max characters per line (default 70)
    """
    print(f"\n{label}")
    print("─" * len(label))
    # textwrap.fill wraps long lines cleanly — useful in a terminal
    wrapped = textwrap.fill(text, width=wrap_width)
    print(wrapped)


def get_user_input(prompt: str) -> str:
    """
    Ask the user for input. Exits cleanly if they press Ctrl+C.

    This is a tiny wrapper that handles KeyboardInterrupt gracefully
    so every app doesn't need its own try/except for Ctrl+C.
    """
    try:
        return input(f"\n{prompt}\n> ").strip()
    except KeyboardInterrupt:
        print("\n\nExiting. Goodbye!")
        sys.exit(0)


def print_section(title: str, content: str, wrap_width: int = 68) -> None:
    """
    Print a named section of structured output with consistent formatting.

    Used by App 02 and later apps that parse Claude's response into sections.
    Handles bullet-point lines specially so they stay indented and readable.

    Args:
        title:      The section label (e.g. "Summary", "Key Points")
        content:    The section text (may contain newlines and bullet points)
        wrap_width: Max characters per line (default 68 — fits a 72-wide terminal)
    """
    print(f"\n  {title}")
    print(f"  {'─' * len(title)}")

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("- "):
            # Bullet point: indent the first line, wrap continuation further in
            wrapped = textwrap.fill(
                line,
                width=wrap_width,
                initial_indent="    ",        # "  - " prefix
                subsequent_indent="      "    # align wrapped text under the bullet
            )
        else:
            wrapped = textwrap.fill(line, width=wrap_width, initial_indent="  ")
        print(wrapped)


def count_words(text: str) -> int:
    """Return the word count of a string."""
    return len(text.split())
