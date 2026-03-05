# App 07 — Meeting Processor

## What It Does

Paste raw meeting notes in any format — transcript, bullet points, shorthand —
and get back a fully structured analysis:

- **Summary** — 2-3 sentence overview of what was decided
- **Participants** — everyone mentioned by name
- **Key Decisions** — explicit agreements reached, with rationale
- **Action Items** — every task, with owner, deadline, and priority
- **Open Questions** — anything unresolved or needing follow-up
- **Next Steps** — forward-looking closing summary

## New Concept: Nested Pydantic Models

App 03 introduced Pydantic for *flat* output — one level of fields.
This app introduces **nested models**: objects that contain lists of other objects.

```python
class ActionItem(BaseModel):
    description: str
    owner: Optional[str] = None
    deadline: Optional[str] = None
    priority: str                    # "high", "medium", "low"

class Decision(BaseModel):
    description: str
    rationale: Optional[str] = None

class MeetingAnalysis(BaseModel):
    summary: str
    participants: list[str]
    decisions: list[Decision]        # ← list of Decision objects
    action_items: list[ActionItem]   # ← list of ActionItem objects
    open_questions: list[str]
    next_steps: str
```

`client.messages.parse(response_format=MeetingAnalysis)` guarantees Claude
returns this exact structure — no parsing, no key errors, no validation code.

## How to Run

```bash
python 07-meeting-processor/app.py
```

Paste your notes, type `END` on its own line, and watch the structured output appear.

## What to Look For

- **Optional fields**: If the notes don't mention a deadline, `deadline` is `None`.
  Python handles this cleanly — no crashes, no empty strings.
- **Priority sorting**: Action items are sorted high → medium → low automatically,
  because the structured output gives you real data to sort on.
- **Owner inference**: Claude assigns "Unassigned" when no owner is stated.
  You can change this behavior by editing the system prompt.

## Try It Yourself

1. **Run a real meeting**: Copy notes from your last team meeting and paste them in.

2. **Test edge cases**:
   - Notes with no action items — what does `action_items` return?
   - Notes with ambiguous owners ("someone from the data team") — what does Claude do?
   - Notes in bullet form vs. paragraph form — does quality differ?

3. **Extend the schema**: Add a `MeetingMetadata` class:
   ```python
   class MeetingMetadata(BaseModel):
       date: Optional[str] = None
       duration_minutes: Optional[int] = None
       meeting_type: str  # "standup", "planning", "retro", "1:1", "all-hands"
   ```
   Then add `metadata: MeetingMetadata` to `MeetingAnalysis`.

4. **Try a different output format**: What if you wanted the action items as a
   Markdown table? Add a `to_markdown()` method to `MeetingAnalysis`.
