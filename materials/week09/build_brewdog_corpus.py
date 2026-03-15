"""
Build BrewDog corpus from The Guardian API.

Run this script once before the workshop session to refresh the pre-built
article dataset with live Guardian API data. Requires a free Guardian API key
from https://open-platform.theguardian.com/access/.

Usage:
    python build_brewdog_corpus.py YOUR_API_KEY

The API key can also be provided via the environment variable GUARDIAN_API_KEY.
Output is saved to: materials/week09/data/brewdog_articles_live.csv
"""

import sys
import os
import time
import csv
import urllib.request
import urllib.parse
import json
from datetime import datetime


# ── Configuration ─────────────────────────────────────────────────────────────

QUERY        = "brewdog"
FROM_DATE    = "2010-01-01"
TO_DATE      = "2025-12-31"
PAGE_SIZE    = 200
ORDER_BY     = "newest"
SHOW_FIELDS  = "headline,bodyText,sectionName,trailText"
BODY_MAX     = 500          # characters to retain from bodyText
RATE_LIMIT   = 0.5          # seconds between requests
PROGRESS_N   = 20           # print progress every N articles

ENDPOINT     = "https://content.guardianapis.com/search"
OUTPUT_PATH  = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data", "brewdog_articles_live.csv"
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_api_key() -> str:
    """Return API key from argv[1] or environment variable."""
    if len(sys.argv) >= 2:
        return sys.argv[1].strip()
    key = os.environ.get("GUARDIAN_API_KEY", "").strip()
    if key:
        return key
    print("ERROR: No Guardian API key supplied.")
    print("Usage: python build_brewdog_corpus.py YOUR_API_KEY")
    print("       or set environment variable GUARDIAN_API_KEY")
    sys.exit(1)


def fetch_page(api_key: str, page: int) -> dict:
    """Fetch one page of results from the Guardian API and return parsed JSON."""
    params = {
        "q":            QUERY,
        "from-date":    FROM_DATE,
        "to-date":      TO_DATE,
        "api-key":      api_key,
        "page-size":    PAGE_SIZE,
        "show-fields":  SHOW_FIELDS,
        "order-by":     ORDER_BY,
        "page":         page,
    }
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"  HTTP error on page {page}: {exc.code} {exc.reason}")
        raise
    except urllib.error.URLError as exc:
        print(f"  URL error on page {page}: {exc.reason}")
        raise


def extract_article(seq_id: int, result: dict) -> dict:
    """Extract a flat row dict from a single Guardian API result object."""
    fields   = result.get("fields", {})
    headline = fields.get("headline", result.get("webTitle", "")).strip()

    # Body: truncate bodyText if available, otherwise fall back to trailText
    body_raw = fields.get("bodyText", "").strip()
    if body_raw:
        body = body_raw[:BODY_MAX]
    else:
        body = fields.get("trailText", "").strip()[:BODY_MAX]

    date_str = result.get("webPublicationDate", "")[:10]   # YYYY-MM-DD
    try:
        year = int(date_str[:4])
    except (ValueError, TypeError):
        year = None

    return {
        "id":               seq_id,
        "date":             date_str,
        "year":             year,
        "headline":         headline,
        "body":             body,
        "section":          fields.get("sectionName", result.get("sectionName", "")).strip(),
        "sentiment_label":  "unlabelled",
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    api_key = get_api_key()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    print("=" * 60)
    print("BrewDog corpus builder — The Guardian API")
    print(f"Query:      {QUERY}")
    print(f"Date range: {FROM_DATE} to {TO_DATE}")
    print(f"Output:     {OUTPUT_PATH}")
    print("=" * 60)

    articles      = []
    seq_id        = 1
    current_page  = 1
    total_pages   = None   # set after first response

    while True:
        print(f"\nFetching page {current_page}" +
              (f" / {total_pages}" if total_pages else "") + " ...", end=" ", flush=True)

        try:
            data = fetch_page(api_key, current_page)
        except Exception:
            print("Skipping page due to error.")
            break

        response = data.get("response", {})
        status   = response.get("status", "")

        if status != "ok":
            print(f"\nAPI returned non-ok status: {status}")
            print(json.dumps(response, indent=2)[:500])
            break

        results     = response.get("results", [])
        total_pages = response.get("pages", 1)
        print(f"got {len(results)} results.")

        for result in results:
            row = extract_article(seq_id, result)
            articles.append(row)
            if seq_id % PROGRESS_N == 0:
                print(f"  ... processed {seq_id} articles so far.")
            seq_id += 1

        if current_page >= total_pages:
            break

        current_page += 1
        time.sleep(RATE_LIMIT)

    # ── Write CSV ─────────────────────────────────────────────────────────────
    if not articles:
        print("\nNo articles retrieved — CSV not written.")
        return

    fieldnames = ["id", "date", "year", "headline", "body", "section", "sentiment_label"]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(articles)

    print(f"\n{'=' * 60}")
    print(f"Done.  {len(articles)} articles saved to:")
    print(f"  {OUTPUT_PATH}")

    # ── Year distribution summary ─────────────────────────────────────────────
    year_counts: dict[int, int] = {}
    for art in articles:
        y = art["year"]
        if y is not None:
            year_counts[y] = year_counts.get(y, 0) + 1

    print(f"\nYear distribution:")
    for year in sorted(year_counts):
        bar = "#" * min(year_counts[year], 50)
        print(f"  {year}: {bar} ({year_counts[year]})")
    print("=" * 60)


if __name__ == "__main__":
    main()
