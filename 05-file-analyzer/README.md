# App 05 — File Analyzer

## What This App Does

Load any file — a document, spreadsheet, config, or PDF — and ask questions
about it in plain English. Claude reads the whole file and answers with
specific references to the actual content. Ask follow-up questions and Claude
builds on what it already read.

---

## What You'll Learn

| Concept | Explanation |
|---------|-------------|
| **File I/O** | Reading and converting different file types to text Claude can use |
| **Document input** | How to inject a whole document into a conversation as context |
| **Context window limits** | What happens as files get larger, and how to handle it |
| **Stateful Q&A** | How to keep conversation history so follow-ups work naturally |
| **Multi-turn document analysis** | Each question builds on the previous without re-sending the file |
| **Format-specific parsing** | Why CSV/JSON need structured loading rather than raw text |

---

## Supported File Types

| Extension | How it's loaded |
|-----------|----------------|
| `.txt` | Read as plain text |
| `.md` | Read as plain text (markdown renders as-is) |
| `.csv` | Parsed into rows/columns with a summary header |
| `.json` | Parsed and pretty-printed with a structure summary |
| `.pdf` | Text extracted page by page using `pypdf` |
| *other* | Attempted as plain text |

---

## How to Run It

```bash
# Interactive — it will ask you for a file path:
python 05-file-analyzer/app.py

# With a file path as argument:
python 05-file-analyzer/app.py path/to/your/file.csv
```

---

## What to Look For

- **Token counts per question** — notice how the first question is expensive
  (it includes the whole file) and follow-ups are much cheaper (file is
  already in history, Claude only needs the new question)
- **How Claude references the file** — it quotes specific rows, keys, or
  passages rather than making things up
- **Follow-up coherence** — ask something like "what was that number again?"
  and see Claude correctly recall from its context
- **File type differences** — the same question on a `.csv` vs a `.txt` gets
  very different treatment

---

## Example Files to Try

You can create test files in the `cc-sandbox` folder:

**sample.csv** — then ask: *"Which row has the highest value in column 3?"*
```
name,score,grade
Alice,92,A
Bob,78,B+
Carol,88,A-
David,95,A+
```

**sample.json** — then ask: *"What are all the keys in this file?"*
```json
{"company": "Acme", "founded": 1985, "employees": 250, "active": true}
```

**Any PDF** — drop in a report, research paper, or contract and ask:
*"Summarise the key points in this document."*

---

## The Key Insight: Send the File Once

```python
# First question — embeds the full file content
user_content = f"Here is the file '{file_name}':\n\n{file_content}\n\nQuestion: {question}"

# Follow-up questions — file is already in the history
user_content = question   # that's it
```

Claude's context window holds the entire conversation. Once the file is in
there, every subsequent question has access to it without re-sending it.
This is why token counts drop sharply after the first question.
