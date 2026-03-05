# App 08 — Excel Agent

## What It Does

Load any CSV or Excel file, then ask questions about it in plain English:

- *"Which product category had the highest revenue?"*
- *"How many rows have missing values in the Status column?"*
- *"What's the average deal size for enterprise customers in Q4?"*
- *"Are there any duplicate email addresses?"*

No SQL. No formulas. No pivot tables. Just questions and answers.

## New Concept: CSV/Excel Parsing + Smart Context Formatting

Getting spreadsheet data into a prompt isn't as simple as pasting the CSV.
Large files won't fit. Even small ones benefit from structure.

This app teaches the **layered context** technique — format the data in layers,
most informative first:

```
1. Shape       → "1,247 rows × 9 columns"
2. Schema      → column names, types, null counts
3. Stats       → min/max/mean/std for numeric columns
4. Top values  → most common values per text column
5. Rows        → full data (small files) or head+tail sample (large files)
```

Claude reads this structure and can answer most questions from the stats and
schema alone — without seeing every row.

```python
# Small files: send everything
if len(df) <= MAX_ROWS_FULL:
    return df.to_string(index=True)

# Large files: send schema + stats + sample
else:
    sample = pd.concat([df.head(15), df.tail(15)])
    return f"[{len(df) - 30} rows not shown...]\n{sample.to_string()}"
```

## How to Run

```bash
python 08-excel-agent/app.py
```

Enter a file path when prompted (drag-and-drop works on most terminals),
then ask questions. Type `new` to load a different file, `quit` to exit.

## What to Look For

- **Schema-first answers**: Ask "What columns does this file have?" — Claude
  answers from the schema section without needing to read all the rows.

- **Aggregate questions**: Ask "What's the average sales amount?" — Claude
  gets this from the `describe()` stats, not by summing every row.

- **Follow-up questions**: Watch the token count grow on each question.
  The data is sent once; subsequent questions only add a few tokens.

- **Large file honesty**: With a file over 200 rows, Claude will say
  "based on the sample shown" — it knows what it hasn't seen.

## Try It Yourself

1. **Create a test CSV** to experiment with:
   ```python
   import pandas as pd
   df = pd.DataFrame({
       "name": ["Alice", "Bob", "Carol", "Dave"],
       "department": ["Engineering", "Marketing", "Engineering", "Sales"],
       "salary": [95000, 72000, 110000, 85000],
       "years": [3, 7, 12, 2]
   })
   df.to_csv("test_data.csv", index=False)
   ```

2. **Try aggregate questions**: "What's the average salary by department?"

3. **Try anomaly detection**: "Are there any outliers in the salary column?"

4. **Try a large file**: Find a public dataset (Kaggle, data.gov) with 1,000+
   rows. Notice how Claude handles the unseen rows in its answers.

5. **Extend the app**: Add a `run_analysis` tool (like App 04's tool loop)
   that executes `df.query()` or `df.groupby()` expressions so Claude can
   explore large files beyond the sample rows.
