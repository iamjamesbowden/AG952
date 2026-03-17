#!/usr/bin/env python3
"""
parse_factiva_rtf.py
────────────────────
Parse all Factiva*.rtf files in ~/Downloads into a single structured CSV.

Output: ~/Downloads/brewdog_articles_factiva.csv

Factiva article metadata structure (fixed, anchored on 'NNN words' line):
    ...
    [author line]
    NNN words          ← anchor
    DD Month YYYY
    Newspaper Name
    NEWSPAPER_CODE
    edition (e.g. "1; National")
    page number
    English
    © copyright line
    [blank]
    [article body text]
    Document XXXXXXXX  ← block separator

Usage:
    python3 parse_factiva_rtf.py [downloads_dir]
"""

import os
import re
import csv
import subprocess
import sys
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
DOWNLOADS     = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads"
OUTPUT_FILE   = DOWNLOADS / "brewdog_articles_factiva.csv"
MIN_WORDS     = 50   # skip very short items (captions, corrections)

MONTHS = {
    "january": "01", "february": "02", "march": "03",  "april":    "04",
    "may":     "05", "june":     "06", "july":  "07",  "august":   "08",
    "september":"09","october":  "10", "november":"11", "december": "12",
}

# Category labels that appear as the first line of some article blocks
SECTION_WORDS = {
    "sport", "news", "business", "features", "feature", "opinion", "comment",
    "finance", "city", "economics", "culture", "lifestyle", "entertainment",
    "technology", "politics", "health", "media", "money", "travel",
    "property", "food", "uk", "world", "scotland", "analysis", "exclusive",
    "interview", "review", "column", "obituary", "obituaries", "letters",
    "comment", "editorial",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def rtf_to_text(path: Path) -> str:
    """Convert RTF to plain text using macOS textutil."""
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        print(f"  ⚠  textutil failed for {path.name}", file=sys.stderr)
        return ""
    return result.stdout


def parse_date(raw: str):
    """Parse 'DD Month YYYY' → ('YYYY-MM-DD', int(YYYY)) or (raw, None)."""
    m = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw.strip())
    if m:
        day, mon_str, year = m.groups()
        mon_num = MONTHS.get(mon_str.lower())
        if mon_num:
            return f"{year}-{mon_num}-{day.zfill(2)}", int(year)
    return raw.strip(), None


def is_section_line(line: str) -> bool:
    """Return True if line looks like a Factiva section/category label."""
    words = set(re.sub(r"[;,/]", " ", line.lower()).split())
    return bool(words) and words.issubset(SECTION_WORDS) and len(line) < 60


def clean_text(text: str) -> str:
    """Normalise whitespace in article body."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# Doc-ID tails left by the split regex are lowercase alphanumeric strings
# that always contain at least one digit (e.g. "em3c00065", "ekbk0005l").
# Real section labels are purely alphabetic ("features", "business"), so
# requiring a digit in the string safely distinguishes the two.
_DOC_FRAG_RE = re.compile(r"^[a-z][a-z0-9]{4,18}$")


def is_doc_frag(s: str) -> bool:
    return bool(_DOC_FRAG_RE.match(s)) and any(c.isdigit() for c in s)


def clean_block(block: str) -> str:
    """Strip form-feeds, leading doc-ID tail fragments, and blank lines."""
    block = block.replace("\x0c", "")   # remove RTF form-feed characters
    lines = block.split("\n")
    while lines:
        s = lines[0].strip()
        if not s or is_doc_frag(s):
            lines.pop(0)
        else:
            break
    return "\n".join(lines)


# ── Article block parser ───────────────────────────────────────────────────────

def parse_block(block: str) -> dict | None:
    """
    Parse one article block (text between 'Document XXXXX' separators).
    Returns a dict of fields or None if the block can't be parsed.
    """
    raw_lines = [l.rstrip() for l in block.split("\n")]

    # 1. Locate the copyright line (marks end of metadata)
    copyright_idx = None
    for i, line in enumerate(raw_lines):
        s = line.strip()
        if not s:
            continue
        # © may appear as the literal © character, \xa9, or as part of "©026..."
        if s[0] in ("©", "\xa9") or s[:3] in ("Cop", "cop") or "©" in s[:8]:
            copyright_idx = i
            break

    if copyright_idx is None:
        return None

    # 2. Article body: everything after copyright, strip leading blank lines
    body_lines = raw_lines[copyright_idx + 1:]
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)
    text = clean_text("\n".join(body_lines))

    # 3. Metadata: everything before copyright line
    meta = [l.strip() for l in raw_lines[:copyright_idx]]

    # 4. Find 'NNN words' anchor line
    wc_idx = None
    for i, line in enumerate(meta):
        if re.match(r"^\d+\s+words?$", line, re.IGNORECASE):
            wc_idx = i
            break

    if wc_idx is None or wc_idx < 1:
        return None

    word_count = int(re.match(r"^(\d+)", meta[wc_idx]).group(1))

    if word_count < MIN_WORDS:
        return None

    # 5. Extract fields relative to anchor
    author_raw = meta[wc_idx - 1]
    date_raw   = meta[wc_idx + 1] if wc_idx + 1 < len(meta) else ""

    # Online articles (FT.com, WSJ online, etc.) insert a HH:MM publication
    # time between the date and the newspaper name.  Detect and skip it.
    offset = 2
    if wc_idx + offset < len(meta) and re.match(r"^\d{1,2}:\d{2}$", meta[wc_idx + offset].strip()):
        offset += 1   # skip timestamp line

    newspaper  = meta[wc_idx + offset]     if wc_idx + offset     < len(meta) else ""
    newsp_code = meta[wc_idx + offset + 1] if wc_idx + offset + 1 < len(meta) else ""

    # Newspaper code should be short uppercase with no spaces; take first token
    newsp_code = newsp_code.split()[0] if newsp_code else ""

    date, year = parse_date(date_raw)
    author = re.sub(r"^By\s+", "", author_raw, flags=re.IGNORECASE).strip()

    # 6. Headline: everything before the author line, minus section labels
    headline_region = [l for l in meta[:wc_idx - 1] if l]
    section = ""
    if headline_region and is_section_line(headline_region[0]):
        section = headline_region[0]
        headline_region = headline_region[1:]

    headline = " ".join(headline_region).strip()

    # 7. Validate
    if not headline or not text or not date:
        return None

    return {
        "headline":       headline,
        "author":         author,
        "date":           date,
        "year":           year,
        "newspaper":      newspaper,
        "newspaper_code": newsp_code,
        "section":        section,
        "word_count":     word_count,
        "text":           text,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    rtf_files = sorted(DOWNLOADS.glob("Factiva*.rtf"))
    if not rtf_files:
        print(f"No Factiva*.rtf files found in {DOWNLOADS}")
        sys.exit(1)

    print(f"Found {len(rtf_files)} RTF files in {DOWNLOADS}\n")

    all_articles: list[dict] = []
    seen: set[tuple] = set()   # (lowercase headline, date) — dedup

    for rtf_path in rtf_files:
        print(f"  {rtf_path.name} … ", end="", flush=True)
        plain_text = rtf_to_text(rtf_path)
        if not plain_text:
            print("SKIPPED (conversion failed)")
            continue

        # Split on Factiva 'Document XXXXXX' separator lines.
        # Original [A-Z0-9]+ regex: correctly splits at the uppercase prefix of
        # each document ID (e.g. 'DAIM000020260312'), leaving the lowercase
        # tail ('em3c00065') at the start of the next block — handled below.
        blocks = re.split(r"\nDocument\s+[A-Z0-9]+", plain_text)

        n = 0
        for block in blocks:
            block = clean_block(block.strip())
            if len(block) < 80:
                continue
            article = parse_block(block)
            if article is None:
                continue
            key = (article["headline"].lower()[:80], article["date"])
            if key in seen:
                continue
            seen.add(key)
            all_articles.append(article)
            n += 1

        print(f"{n} articles")

    if not all_articles:
        print("\nNo articles parsed. Check RTF format.")
        sys.exit(1)

    # Sort by date then headline
    all_articles.sort(key=lambda a: (a["date"] or "", a["headline"]))

    # Assign sequential IDs
    for i, a in enumerate(all_articles, 1):
        a["id"] = i

    # Write CSV
    fields = [
        "id", "headline", "author", "date", "year",
        "newspaper", "newspaper_code", "section", "word_count", "text",
    ]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_articles)

    # Summary
    years   = sorted(set(a["year"] for a in all_articles if a["year"]))
    papers  = {}
    for a in all_articles:
        papers[a["newspaper"]] = papers.get(a["newspaper"], 0) + 1

    print(f"\n{'─'*50}")
    print(f"Total articles:  {len(all_articles):,}")
    print(f"Date range:      {years[0]} – {years[-1]}" if years else "Date range: unknown")
    print(f"Output:          {OUTPUT_FILE}")
    print(f"\nTop newspapers:")
    for paper, count in sorted(papers.items(), key=lambda x: -x[1])[:12]:
        print(f"  {paper:<35} {count:>5}")
    print("─"*50)


if __name__ == "__main__":
    main()
