# AG983 Assignment 2026 — Corpus Build Instructions

Run these steps once before releasing the assignment.
The script downloads 10-K filings from EDGAR and writes four corpus CSV files
that students load automatically when they run the assignment notebook.

---

## Prerequisites

```bash
pip install requests beautifulsoup4 pandas lxml
```

Ensure you have an active internet connection. EDGAR enforces a soft rate limit
of 10 requests per second; the script sleeps 0.15 s between requests.
Allow **50–80 minutes** for the full run (all four scenarios).

---

## Scenarios

| Scenario | Theme | Firms | Period | Expected rows (approx) |
|---|---|---|---|---|
| A | Cybersecurity Risk Disclosure | 51 | 2019–2024 | ~600 |
| B | Consumer ESG and Greenwashing | 49 | 2019–2024 | ~580 |
| C | Pharmaceutical Liability and Opioid Litigation | 31 | 2015–2024 | ~580 |
| D | Real Estate and Interest Rate Risk | 50 | 2018–2024 | ~680 |

Each row is one (firm × year × section) combination.
Two sections are extracted per filing: `item_1a` and `item_7`.

---

## Step 1 — Clone this repository

```bash
git clone https://github.com/iamjamesbowden/AG952.git
cd AG952
```

---

## Step 2 — Run the corpus builder

All four scenarios at once:

```bash
python AG983/scripts/build_corpus.py
```

Or one scenario at a time (safe to re-run after interruption):

```bash
python AG983/scripts/build_corpus.py --scenario A
python AG983/scripts/build_corpus.py --scenario B
python AG983/scripts/build_corpus.py --scenario C
python AG983/scripts/build_corpus.py --scenario D
```

Progress is logged to the terminal and to `AG983/data/build_corpus.log`.
The script resumes automatically if interrupted.

---

## Step 3 — Verify output

```python
import pandas as pd
for s in ["a", "b", "c", "d"]:
    p = f"AG983/data/scenario_{s}/corpus.csv"
    try:
        df = pd.read_csv(p)
        print(f"scenario_{s}: {len(df):>4} rows | {df['firm'].nunique()} firms | sections {sorted(df['section'].unique())}")
    except FileNotFoundError:
        print(f"scenario_{s}: MISSING")
```

---

## Step 4 — When moving to AG983 repo

When this material moves to `iamjamesbowden/AG983`, update the following:

1. `AG983/scripts/build_corpus.py` — `REPO_ROOT` is derived from `Path(__file__).resolve().parents[2]`
   (currently parents[3] to account for the AG952 wrapper). Adjust depth if needed.
2. Notebook Cell 2 — update `APPS_SCRIPT_URL` to the new AG983 Apps Script endpoint.
3. Notebook Step 0 — `REPO_URL` already points to `iamjamesbowden/AG983.git` (correct for production).

---

## Corpus format

| Column | Description |
|---|---|
| `cik` | SEC Central Index Key |
| `firm` | Company name |
| `ticker` | Stock ticker |
| `category` | Sub-group within scenario |
| `year` | Fiscal year |
| `section` | `item_1a` or `item_7` |
| `filing_date` | Date filed with SEC |
| `accession_number` | EDGAR accession number |
| `text` | Cleaned plain text |
| `word_count` | Whitespace-delimited token count |

Scenario C also includes a `litigation_status` column (`defendant` or `adjacent`).
