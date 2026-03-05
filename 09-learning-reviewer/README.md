# App 09 — Learning Reviewer

## What It Does

Submit any content — a document, training module, email, or presentation outline —
and get a structured quality review scored against a rubric:

- **Criterion-by-criterion scores** (1–5) with specific rationale and quotes
- **Improvement suggestions** that tell you exactly what to change
- **Top strengths** — what's working well
- **Priority improvements** — highest-leverage changes first

Built-in rubrics include one **directly aligned to 70-20-10 learning design**
for reviewing L&D content.

## New Concept: Domain-Specific Prompting + Dynamic System Prompts

Apps 01–08 used fixed system prompts. App 09 **builds the system prompt at runtime**
from the chosen rubric:

```python
def build_system_prompt(rubric_name: str, criteria: list[str]) -> str:
    criteria_block = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(criteria))
    return f"""You are reviewing against the "{rubric_name}" rubric.

Rubric criteria:
{criteria_block}

Scoring guide:
  5 — Excellent ...
  4 — Good ...
  ..."""
```

Different rubric → different expert reviewer persona → different output.
No code changes. Just a different list of criteria.

This is **domain-specific prompting**: instead of a generic assistant,
you get a specialist evaluator with a precise lens.

## Built-in Rubrics

| # | Name | Best For |
|---|------|----------|
| 1 | Professional Writing | Documents, emails, reports |
| 2 | Technical Documentation | READMEs, API docs, SOPs |
| 3 | **Learning Content (70-20-10 Aligned)** | **L&D modules, training materials** |
| 4 | Presentation / Slide Deck Outline | Decks, talk outlines |
| 5 | Custom | Any domain you define |

## How to Run

```bash
python 09-learning-reviewer/app.py
```

Choose a rubric, paste your content (or load from a file), and review.

## What to Look For

- **Quoted evidence**: Claude quotes specific phrases from your content
  as evidence for each score — not vague impressions.
- **Actionable suggestions**: Each criterion gets one concrete improvement,
  not generic advice like "be clearer."
- **Rubric 3 in action**: If you're building L&D content, use rubric 3.
  Claude scores how well your content covers the 70% (experiential),
  20% (social), and 10% (formal) dimensions.
- **Custom rubrics**: Enter your own criteria and get a specialist
  reviewer in 30 seconds.

## Try It Yourself

1. **Review a real document**: Paste a training module, email, or report
   you've written. How does it score?

2. **Compare rubrics**: Submit the same content twice with different rubrics.
   Notice how the same text reads differently through a "Professional Writing"
   lens vs. a "70-20-10" lens.

3. **Build a custom rubric** for your team's specific needs:
   ```
   McKinsey Communication Standard
   ────────────────────────────────
   Criterion 1: Pyramid structure — Does it lead with the conclusion?
   Criterion 2: So what — Is the "so what" for the reader explicit?
   Criterion 3: Specificity — Are all claims backed with data or examples?
   Criterion 4: Brevity — Could any sentence be cut without losing meaning?
   Criterion 5: Action orientation — Does it drive a clear decision or next step?
   ```

4. **Extend the schema**: Add a `revised_opening: str` field to `ReviewResult`
   — have Claude rewrite the opening paragraph based on its own feedback.
