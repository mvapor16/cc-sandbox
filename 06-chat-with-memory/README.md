# App 06 — Chat with Memory

## What This App Does

A terminal chatbot that genuinely remembers everything you've said. Mention
your name, a project, a preference — bring it up five messages later and
Claude will recall it. The longer the conversation, the richer the context.

---

## What You'll Learn

| Concept | Explanation |
|---------|-------------|
| **Conversation history** | How the `messages` array creates the illusion of memory |
| **Stateless API** | Why Claude has no memory by default, and why *you* supply it |
| **User/assistant alternation** | The strict turn structure every conversation must follow |
| **Context window growth** | How token costs accumulate over a long conversation |
| **What "memory" really is** | Claude re-reads the full transcript every turn — it's not recall, it's replay |
| **History manipulation** | Why you can edit, delete, or fabricate history — and what that implies |

---

## The Core Insight

```python
# This is the entire "memory" system — one list:
messages = []

# Every turn: append user message, call API, append response
messages.append({"role": "user",      "content": user_input})
messages.append({"role": "assistant", "content": response})

# The ENTIRE list is sent on every API call
response = client.messages.create(messages=messages, ...)
```

Claude has no persistent state. It sees a fresh context window every call.
"Memory" is just the history you pass in. This means:

- **You control the memory** — you can edit, delete, or inject messages
- **Cost grows over time** — you're billed for every token in history, every turn
- **Privacy matters** — the full transcript is re-sent to the API each turn
- **Context limits apply** — very long conversations eventually exceed the window

---

## Commands

```
/help      Show available commands
/clear     Wipe history and start fresh
/history   Show the full conversation transcript
/save      Export to a timestamped .txt file
/tokens    Show how many tokens this session has used
/quit      Exit
```

---

## How to Run It

```bash
source venv/bin/activate
python 06-chat-with-memory/app.py
```

---

## What to Look For

**Watch the token counts** after each message:
```
── turn 3  in: 1,847  out: 124  session: 4,201 tokens
── turn 4  in: 2,105  out: 98   session: 6,404 tokens
── turn 5  in: 2,312  out: 156  session: 8,872 tokens
```

Notice how `in` (input tokens) grows with every turn. That's because the
entire conversation history is re-sent on every API call. Output tokens
stay roughly constant — Claude is only generating one reply at a time.

Run `/tokens` at any point to see the full breakdown.

---

## Experiment Ideas

1. **Test recall**: Tell Claude your name in turn 1, then ask "What's my name?"
   ten turns later. It will know.

2. **Watch costs grow**: Use `/tokens` every few turns to see input tokens climb.

3. **Try /clear**: Notice how Claude immediately forgets everything after a clear.
   This proves the memory is entirely in the `messages` list — not in Claude.

4. **Force a mistake**: After many turns, ask Claude to recall something you
   *didn't* say. Good models acknowledge they don't have that information.
