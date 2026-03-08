# AG952 Assignment 2026 — Corpus Build Instructions

Run these steps once before releasing the assignment on 10 March 2026.
The script downloads 10-K filings from EDGAR and writes four corpus CSV files
that students load automatically when they run the assignment notebook.

---

## Prerequisites

```bash
pip install requests beautifulsoup4 pandas lxml
```

You must be connected to the internet. EDGAR enforces a soft rate limit of
10 requests per second; the script sleeps 0.15 s between requests. Allow
**30–50 minutes** for the full run (all four scenarios).

---

## Step 1 — Pull the latest repository

```bash
cd /path/to/AG952
git pull origin main
```

---

## Step 2 — Run the corpus builder

Run all four scenarios at once:

```bash
python assignments/march2026/scripts/build_corpus.py
```

Or run one scenario at a time (useful if interrupted):

```bash
python assignments/march2026/scripts/build_corpus.py --scenario A
python assignments/march2026/scripts/build_corpus.py --scenario B
python assignments/march2026/scripts/build_corpus.py --scenario C
python assignments/march2026/scripts/build_corpus.py --scenario D
```

The script resumes automatically: if a corpus.csv already exists it skips
filings that are already saved, so it is safe to re-run after an interruption.

Progress is logged to the terminal and to:

```
assignments/march2026/data/build_corpus.log
```

---

## Step 3 — Verify the output

After the run, confirm all four files exist and have the expected row counts:

```bash
python - <<'EOF'
import pandas as pd
for s in ["a", "b", "c", "d"]:
    p = f"assignments/march2026/data/scenario_{s}/corpus.csv"
    try:
        df = pd.read_csv(p)
        firms  = df["firm"].nunique()
        years  = sorted(df["year"].unique())
        sects  = sorted(df["section"].unique())
        print(f"scenario_{s}: {len(df):>4} rows | {firms} firms | years {years} | sections {sects}")
    except FileNotFoundError:
        print(f"scenario_{s}: MISSING")
EOF
```

Expected approximate row counts (3 sections × firms × years):

| Scenario | Firms | Years | Expected rows (approx) |
|---|---|---|---|
| A | 20 | 5 | ~300 |
| B | 40 | 2–3 | ~240 |
| C | 25 | 3 | ~225 |
| D | 25 | 4 | ~300 |

Not every section is present in every filing; actual counts will be slightly lower.

---

## Step 4 — Commit and push the data files

```bash
cd /path/to/AG952

git add assignments/march2026/data/scenario_a/corpus.csv \
        assignments/march2026/data/scenario_b/corpus.csv \
        assignments/march2026/data/scenario_c/corpus.csv \
        assignments/march2026/data/scenario_d/corpus.csv

git commit -m "Add AG952 assignment corpora (scenarios A-D) from EDGAR

Item 1A, Item 7, and Item 7A extracted from 10-K filings.
See assignments/march2026/scripts/build_corpus.py for firm lists."

git push origin main
```

---

## Step 5 — Confirm Colab access

Visit the Colab link and run Cell 3 (Load corpus). Confirm the corpus loads
without a FileNotFoundError and that the shape, column names, and sample rows
look reasonable.

```
https://colab.research.google.com/github/iamjamesbowden/AG952/blob/main/assignments/march2026/AG952_Assignment_2026.ipynb
```

---

## Corpus format

Each corpus CSV has the following columns:

| Column | Description |
|---|---|
| `cik` | SEC Central Index Key |
| `firm` | Company name |
| `ticker` | Stock ticker |
| `category` | Sub-group within scenario (e.g. oil_gas, renewable, distressed) |
| `year` | Fiscal year |
| `section` | `item_1a`, `item_7`, or `item_7a` |
| `filing_date` | Date the 10-K was filed with the SEC |
| `accession_number` | EDGAR accession number for the source filing |
| `text` | Cleaned plain text of the section |
| `word_count` | Number of whitespace-delimited tokens in `text` |

Scenario B also includes a `bk_year` column for distressed firms (the year
Chapter 11 was filed).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | `pip install requests beautifulsoup4 pandas lxml` |
| Row count much lower than expected | Some filings use exhibit files; re-run with `--scenario X` to retry |
| `ConnectionError` or repeated timeouts | Check internet; EDGAR may be under maintenance |
| Section text suspiciously short (<500 words) | The TOC-skip logic in `extract_section` advances past table-of-contents entries; check the filing manually if needed |
