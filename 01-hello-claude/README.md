# App 01 — Hello, Claude

## What This App Does

Sends a single message to Claude and prints the response.
That's it. The goal isn't the output — it's understanding *every moving part*
so nothing feels like magic going forward.

---

## What You'll Learn

| Concept | Explanation |
|---------|-------------|
| **API call** | How your Python code reaches Claude over the internet |
| **System prompt** | How you give Claude a role or persona before the conversation starts |
| **Messages array** | The structure every Claude conversation lives in |
| **Tokens** | How text is measured — affects cost and context limits |
| **Stop reason** | How Claude tells you why it finished responding |

---

## How to Run It

```bash
# From the cc-sandbox root:
source venv/bin/activate          # activate your virtual environment
python 01-hello-claude/app.py     # run the app
```

You should see:
```
────────────────────────────────────────────────────────────
  App 01 — Hello, Claude
────────────────────────────────────────────────────────────
Model  : claude-opus-4-6
Message: Hello! I just ran my first agentic app. What did I just do?

Sending message to Claude...

Claude says:
──────────
[Claude's response appears here]

Token usage:
  Input  (your message + system prompt) : ~120
  Output (Claude's response)            : ~150
  Total                                 : ~270

Stop reason: end_turn
```

---

## Key Things to Notice

**The pause.** When you run the script, it hangs for a second before printing.
That pause is the network round-trip to Anthropic's servers and Claude thinking.
In later apps we'll use *streaming* to make text appear word-by-word instead
of all at once.

**Token counts.** Your message was maybe 15 words, but the input tokens are
higher — because the *system prompt* is also counted. Everything Claude reads
costs tokens.

**`stop_reason: end_turn`.** This means Claude finished naturally.
If you ever see `max_tokens`, you've hit your limit — increase `max_tokens`.

---

## The Code, Line by Line

Open `app.py`. Every section has a comment block explaining:
- What the code does
- *Why* it's written this way
- What happens if you change it

Key sections to read:
1. `SYSTEM_PROMPT` — try changing this to "You are a pirate" and re-run
2. `USER_MESSAGE` — change this to any question you like
3. `client.messages.create(...)` — this is the core call you'll use in every app
4. `response.content[0].text` — how to extract Claude's reply
5. `response.usage` — token counts

---

## Try It Yourself

After running it once, experiment:

1. **Change the message** — edit `USER_MESSAGE` to ask anything
2. **Change the system prompt** — make Claude a McKinsey analyst, a teacher, a chef
3. **Lower max_tokens to 50** — watch Claude get cut off mid-sentence
4. **Print the whole response object** — add `print(response)` to see everything

---

## What's Next

`02-smart-summarizer/` — You'll paste in a block of text and Claude will
return a structured summary with key points, action items, and a one-liner.
New concept: **prompt engineering** (how you ask shapes what you get).
