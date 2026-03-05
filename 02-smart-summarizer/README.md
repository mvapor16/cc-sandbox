# App 02 — Smart Summarizer

## What You Built

A terminal tool that accepts any text — an article, an email, a report, meeting notes — and returns a structured analysis from Claude:

- **Summary** — 2–3 sentences capturing the core idea
- **Key Points** — the most important specific claims
- **Takeaway** — the single most important sentence in the whole text
- **Sentiment** — Positive / Neutral / Negative / Mixed, with reason
- **Reading Level** — Simple / Moderate / Technical, with reason

---

## The New Concept: Prompt Engineering + Structured Output

App 01 proved you could talk to Claude. App 02 proves you can *control* what Claude gives back.

### Why this matters

In App 01, Claude responded however it felt appropriate — conversational, variable length, unpredictable shape. That's fine for chat. It's useless if you want to parse the output, display it in a UI, or feed it to another process.

**Prompt engineering** is the discipline of writing instructions to Claude so precisely that the output shape is reliable. It's the difference between "give me a summary" and "return exactly these five labelled sections in this order."

**Structured output** (text-based) is the result: Claude's response can be split, parsed, and used as data — not just read as prose. App 03 will introduce JSON output, which is even more structured. But markdown-section-based output like this is simpler, more readable in logs, and often all you need.

---

## How to Run

```bash
# From the repo root
python 02-smart-summarizer/app.py
```

Paste any text when prompted. Press **Enter on a blank line** when you're done.

---

## What to Observe

### 1. The system prompt is doing real work
Open `app.py` and read `SYSTEM_PROMPT`. Notice:
- It names exact section headers — `## SUMMARY`, `## KEY POINTS`, etc.
- It explicitly forbids preamble ("Do not write anything before `## SUMMARY`")
- It tells Claude exactly how to format bullet points
- It defines the vocabulary Claude must use ("Positive / Neutral / Negative / Mixed")

Remove any one of those constraints and run the app again. Watch how the output drifts.

### 2. The parser is simple because the format is strict
`parse_sections()` in `app.py` is only ~15 lines. It works because Claude reliably returns `## HEADER` markers. The prompt engineering makes the parsing trivial.

### 3. Token counts go up with input length
In App 01 your input was ~10 words. Here you're sending whole articles. Watch the `input_tokens` number — it grows linearly with the text you paste. This is how cost and context limits work in practice.

### 4. The five sections tell you different things
- **Summary** = compression (same idea, fewer words)
- **Key Points** = extraction (pull out the important claims)
- **Takeaway** = distillation (what's the one thing?)
- **Sentiment** = classification (categorise + explain)
- **Reading Level** = meta-analysis (Claude reasoning about the text's own properties)

Each of these is a different type of reasoning task — all done in one API call.

---

## Try It With These Texts

**Short news article** — paste any paragraph from a news site. Try BBC, Reuters, or the FT.

**Email thread** — paste a work email (redact names if needed). See how Claude extracts action items as key points.

**McKinsey insight** — paste an excerpt from a McKinsey article or client brief. Notice how it handles technical/consulting language in the Reading Level field.

**Your own writing** — paste something you wrote. The Takeaway section often surprises authors.

---

## Key Questions to Think About

1. **What happens if Claude doesn't follow the format?**
   Try shortening the system prompt drastically and see how quickly the output becomes unparseable. The app handles missing sections gracefully — check `display_analysis()` to see how.

2. **What would you add to the system prompt to make it better?**
   Could you add a `## RECOMMENDED ACTIONS` section? What would you need to change in the prompt *and* the parser?

3. **When would text-based structured output break down?**
   If Claude is unsure which section a point belongs to, it might put it in the wrong place. This is why App 03 introduces JSON — it's harder to misplace a key in a JSON object than a section in markdown text.

---

## What Changed From App 01

| | App 01 | App 02 |
|---|---|---|
| Input | Hardcoded string | User types/pastes at runtime |
| System prompt | Vague personality instruction | Precise output format specification |
| Output | Free-form prose | Five labelled, parseable sections |
| What you do with the response | Print it | Parse it into a dict, display by section |
| Token count | ~80 input | Grows with input text length |

---

## Files

```
02-smart-summarizer/
├── app.py      ← all the logic, heavily commented
└── README.md   ← you are here
```

The `shared/helpers.py` file was updated to add `print_section()` — a utility
that formats each section with consistent indentation and line-wrapping.
It's used here and will be used in later apps.

---

*Next: App 03 — Document Classifier. Claude reads a document and returns a category, confidence score, and reasoning — in JSON.*
