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


def count_words(text: str) -> int:
    """Return the word count of a string."""
    return len(text.split())
