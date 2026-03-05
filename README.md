# cc-sandbox — Agentic App Learning Lab

A progressive series of agentic applications built with the Claude API.
Each app teaches one new concept on top of everything before it —
from a single API call all the way to real-time dashboards with multi-agent backends.

---

## How This Works

Every folder is a self-contained app with its own `README.md` that explains:
- **What it does** — in plain English
- **What concept it teaches** — the one new thing introduced
- **How to run it** — exact commands
- **What to look for** — what to pay attention to as it runs

---

## Prerequisites (do this once)

### 1. Get your Anthropic API key
Sign up at [console.anthropic.com](https://console.anthropic.com) and create an API key.

### 2. Create your `.env` file
In the root of this repo, create a file called `.env`:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```
> This file is listed in `.gitignore` — it will **never** be committed to GitHub.

### 3. Set up Python (do this once per machine)
```bash
python -m venv venv          # create a virtual environment
source venv/bin/activate     # activate it (Mac/Linux)
venv\Scripts\activate        # activate it (Windows)
pip install -r requirements.txt  # install all dependencies
```

> **Every time you open a new terminal**, run `source venv/bin/activate` before running any app.

---

## The Learning Path

### Stage 1 — Foundation
*Single API calls. No tools, no server. Just Python + Claude.*

| App | What You Build | New Concept |
|-----|---------------|-------------|
| `01-hello-claude/` | A script that talks to Claude | API call, system prompts, tokens |
| `02-smart-summarizer/` | Paste text, get a structured summary | Prompt engineering, structured output |
| `03-document-classifier/` | Feed a document, get a category + confidence | JSON output, few-shot examples |

### Stage 2 — Tools & Memory
*Agents that can reach outside themselves.*

| App | What You Build | New Concept |
|-----|---------------|-------------|
| `04-web-researcher/` | Ask a question, Claude searches and synthesizes | Tool use, agentic loops |
| `05-file-analyzer/` | Drop a file in, Claude reads and analyzes it | File I/O, document input |
| `06-chat-with-memory/` | A chatbot that remembers the conversation | Conversation history, stateful agents |

### Stage 3 — Real Work
*Business-relevant automation grounded in real scenarios.*

| App | What You Build | New Concept |
|-----|---------------|-------------|
| `07-meeting-processor/` | Paste meeting notes → action items, owners, summary | Multi-output formatting |
| `08-excel-agent/` | Upload a spreadsheet, ask questions in plain English | CSV/Excel parsing, data Q&A |
| `09-learning-reviewer/` | Submit content for AI quality review against a rubric | Domain-specific prompting, evaluation |

### Stage 4 — Pipelines & Web UI
*Multi-step workflows with a real browser interface.*

| App | What You Build | New Concept |
|-----|---------------|-------------|
| `10-research-reporter/` | Topic in → formatted report out | Flask server, sequential chaining |
| `11-skill-gap-advisor/` | Skill gap in → personalized learning path out | Conditional logic, structured reasoning |
| `12-process-documenter/` | Describe a process → Claude writes the SOP | Template-driven generation |

### Stage 5 — Real-Time & Multi-Agent
*Live-updating interfaces and agents that coordinate.*

| App | What You Build | New Concept |
|-----|---------------|-------------|
| `13-writer-reviewer/` | One agent writes, another critiques, loop refines | Multi-agent roles, critique loops |
| `14-brief-generator/` | Full pipeline: research → structure → draft → review | Orchestrator + specialist agents |
| `15-admin-dashboard/` | Live dashboard: agents running, data updating, controls | WebSockets, database, admin backend |

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python | Backend language — glue between Claude and everything else |
| `anthropic` | Official Python SDK for the Claude API |
| `flask` | Lightweight web server (added in Stage 4) |
| `python-dotenv` | Loads your `.env` API key safely |
| SQLite | Embedded database for persistence (Stage 5) |
| HTML/CSS/JS | Frontend interfaces — starting simple, growing sophisticated |

---

## File Structure

```
cc-sandbox/
├── .env                  ← your API key (never committed)
├── .gitignore
├── README.md             ← you are here
├── requirements.txt      ← all Python dependencies
│
├── shared/               ← reusable utilities across all apps
│   ├── claude_client.py  ← single place to configure the API client
│   └── helpers.py        ← common utility functions
│
├── 01-hello-claude/
│   ├── app.py
│   └── README.md
│
└── ... (more apps as we build them)
```
