# App 04 — Web Researcher

## What This App Does

You type any research question. Claude searches the web, reads the relevant
pages, and synthesizes a clear, sourced answer — entirely on its own.

---

## What You'll Learn

| Concept | Explanation |
|---------|-------------|
| **Tool use** | How to give Claude functions it can call (search, fetch URLs) |
| **Tool definitions** | How `name`, `description`, and `input_schema` work together |
| **Agentic loop** | The call → tool_use → execute → return results → repeat cycle |
| **stop_reason** | `"tool_use"` means Claude wants a tool; `"end_turn"` means it's done |
| **tool_use blocks** | How Claude communicates which tool to run and with what arguments |
| **tool_result blocks** | How your code sends execution results back to Claude |
| **Growing messages array** | How the full search + read history accumulates per query |

---

## The Key Pattern: The Agentic Loop

```
You ask a question
        ↓
Claude receives question + tool definitions
        ↓
Claude decides to search       [stop_reason: "tool_use"]
        ↓
Your code runs web_search()
        ↓
Your code sends results back   [role: "user", type: "tool_result"]
        ↓
Claude reads results, decides to fetch a page  [stop_reason: "tool_use"]
        ↓
Your code runs fetch_webpage()
        ↓
Your code sends page content back
        ↓
Claude writes final answer     [stop_reason: "end_turn"]
```

This loop is the foundation of every agentic AI system. Study `app.py`'s
`research()` function — you will write variations of it in every app
from here on.

---

## How to Run It

```bash
# From the cc-sandbox root:
source venv/bin/activate
python 04-web-researcher/app.py
```

---

## What to Look For

- **The progress indicator** in the terminal — each `[tool: argument]` line
  is Claude making a decision in real time
- **How many iterations** a single question requires (usually 2–4 tool calls)
- **The messages array** growing: user question → assistant tool_use →
  user tool_result → assistant tool_use → user tool_result → assistant answer
- **Claude's sourcing behaviour** — it naturally cites URLs when it has them

---

## Example Questions to Try

```
What is the James Webb Space Telescope and what has it discovered?

Who founded Anthropic and what is their mission?

What is the current state of nuclear fusion energy research?

How does the attention mechanism in transformers work?
```

---

## Tools Used in This App

| Tool | What it does | Implementation |
|------|-------------|----------------|
| `web_search` | Finds relevant sources via DuckDuckGo | DuckDuckGo Instant Answer API (free, no key) |
| `fetch_webpage` | Reads full page text | `requests` + HTML stripping |

> **Note on DuckDuckGo:** The free Instant Answer API works best for well-known
> topics. For very specific queries it may return sparse results — this is
> realistic! Claude handles it by trying different search terms, which is
> itself an important agentic behaviour to observe.
