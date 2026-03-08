#!/usr/bin/env python3
"""
AG952 Assignment 2026 — EDGAR corpus builder
=============================================
Downloads Item 1A (Risk Factors) text from 10-K filings on EDGAR for each of
the four research scenarios and writes one corpus.csv per scenario to:

    assignments/march2026/data/scenario_a/corpus.csv
    assignments/march2026/data/scenario_b/corpus.csv
    assignments/march2026/data/scenario_c/corpus.csv
    assignments/march2026/data/scenario_d/corpus.csv

Usage
-----
Run from the repository root:

    pip install requests beautifulsoup4 pandas lxml
    python assignments/march2026/scripts/build_corpus.py

The script respects EDGAR's rate-limit guideline (max 10 req/s); it sleeps
0.15 s between requests. Expect approximately 20-40 minutes total.

Output columns
--------------
    cik, firm, ticker, category, year, filing_date,
    accession_number, item_1a_text, word_count

For Scenario B only, `category` is "distressed" or "control".
"""

import os
import re
import csv
import time
import json
import logging
import requests
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
import warnings

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT   = Path(__file__).resolve().parents[3]   # …/AG952
DATA_ROOT   = REPO_ROOT / "assignments" / "march2026" / "data"
LOG_FILE    = DATA_ROOT / "build_corpus.log"

HEADERS     = {"User-Agent": "AG952 Research iamjamesbowden@users.noreply.github.com"}
RATE_SLEEP  = 0.15   # seconds between every EDGAR request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, mode="w"),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Firm lists
# ---------------------------------------------------------------------------

# ── Scenario A: Climate and ESG Risk Language in the US Energy Sector 2019-2023 ──
SCENARIO_A = [
    # Oil & gas majors
    {"cik": "34088",   "firm": "ExxonMobil",             "ticker": "XOM",  "category": "oil_gas"},
    {"cik": "93410",   "firm": "Chevron",                "ticker": "CVX",  "category": "oil_gas"},
    {"cik": "1163165", "firm": "ConocoPhillips",         "ticker": "COP",  "category": "oil_gas"},
    {"cik": "1038357", "firm": "Pioneer Natural Resources","ticker": "PXD", "category": "oil_gas"},
    {"cik": "821189",  "firm": "EOG Resources",          "ticker": "EOG",  "category": "oil_gas"},
    {"cik": "1090012", "firm": "Devon Energy",           "ticker": "DVN",  "category": "oil_gas"},
    {"cik": "4447",    "firm": "Hess Corporation",       "ticker": "HES",  "category": "oil_gas"},
    # Integrated utilities
    {"cik": "753308",  "firm": "NextEra Energy",         "ticker": "NEE",  "category": "utility"},
    {"cik": "1326160", "firm": "Duke Energy",            "ticker": "DUK",  "category": "utility"},
    {"cik": "92122",   "firm": "Southern Company",       "ticker": "SO",   "category": "utility"},
    {"cik": "715957",  "firm": "Dominion Energy",        "ticker": "D",    "category": "utility"},
    {"cik": "8192",    "firm": "Exelon",                 "ticker": "EXC",  "category": "utility"},
    {"cik": "4904",    "firm": "American Electric Power","ticker": "AEP",  "category": "utility"},
    {"cik": "23632",   "firm": "Consolidated Edison",    "ticker": "ED",   "category": "utility"},
    # Pure-play renewables
    {"cik": "1274494", "firm": "First Solar",            "ticker": "FSLR", "category": "renewable"},
    {"cik": "1409375", "firm": "Sunrun",                 "ticker": "RUN",  "category": "renewable"},
    {"cik": "1463101", "firm": "Enphase Energy",         "ticker": "ENPH", "category": "renewable"},
    {"cik": "867773",  "firm": "SunPower",               "ticker": "SPWR", "category": "renewable"},
    {"cik": "1093691", "firm": "Plug Power",             "ticker": "PLUG", "category": "renewable"},
    {"cik": "1738483", "firm": "Clearway Energy",        "ticker": "CWEN", "category": "renewable"},
]
YEARS_A = [2019, 2020, 2021, 2022, 2023]


# ── Scenario B: Narrative Predictors of Corporate Financial Distress 2015-2023 ──
# For each distressed firm, bk_year is the bankruptcy filing year.
# The script collects the 10-K filings for the 2-3 fiscal years before bk_year.
# Control firms are matched by industry; the script collects the same year range.
SCENARIO_B = [
    # ── Distressed firms ──────────────────────────────────────────────────────
    # 2020 wave
    {"cik": "895126",  "firm": "Chesapeake Energy",       "ticker": "CHK",  "category": "distressed", "bk_year": 2020},
    {"cik": "20520",   "firm": "Frontier Communications", "ticker": "FTR",  "category": "distressed", "bk_year": 2020},
    {"cik": "1255474", "firm": "Whiting Petroleum",       "ticker": "WLL",  "category": "distressed", "bk_year": 2020},
    {"cik": "1166928", "firm": "JC Penney",               "ticker": "JCP",  "category": "distressed", "bk_year": 2020},
    {"cik": "47987",   "firm": "Hertz Global Holdings",   "ticker": "HTZ",  "category": "distressed", "bk_year": 2020},
    {"cik": "78890",   "firm": "Pier 1 Imports",          "ticker": "PIR",  "category": "distressed", "bk_year": 2020},
    {"cik": "1092234", "firm": "Tuesday Morning",         "ticker": "TUEM", "category": "distressed", "bk_year": 2020},
    {"cik": "945764",  "firm": "Denbury Resources",       "ticker": "DNR",  "category": "distressed", "bk_year": 2020},
    {"cik": "1486159", "firm": "Oasis Petroleum",         "ticker": "OAS",  "category": "distressed", "bk_year": 2020},
    {"cik": "1609702", "firm": "California Resources",    "ticker": "CRC",  "category": "distressed", "bk_year": 2020},
    # 2018-2019 wave
    {"cik": "1004440", "firm": "PG&E",                    "ticker": "PCG",  "category": "distressed", "bk_year": 2019},
    {"cik": "1456501", "firm": "Sears Holdings",          "ticker": "SHLD", "category": "distressed", "bk_year": 2018},
    {"cik": "739708",  "firm": "iHeartMedia",             "ticker": "IHRT", "category": "distressed", "bk_year": 2018},
    {"cik": "1282266", "firm": "Windstream Holdings",     "ticker": "WIN",  "category": "distressed", "bk_year": 2019},
    {"cik": "1005210", "firm": "Nine West Holdings",      "ticker": "JNY",  "category": "distressed", "bk_year": 2018},
    # 2021-2023 wave
    {"cik": "887921",  "firm": "Revlon",                  "ticker": "REV",  "category": "distressed", "bk_year": 2022},
    {"cik": "886158",  "firm": "Bed Bath and Beyond",     "ticker": "BBBY", "category": "distressed", "bk_year": 2023},
    {"cik": "84129",   "firm": "Rite Aid",                "ticker": "RAD",  "category": "distressed", "bk_year": 2023},
    {"cik": "1801762", "firm": "WeWork",                  "ticker": "WE",   "category": "distressed", "bk_year": 2023},
    {"cik": "1540159", "firm": "Party City",              "ticker": "PRTY", "category": "distressed", "bk_year": 2023},
    # ── Control firms (same industries, no bankruptcy) ─────────────────────
    {"cik": "1090012", "firm": "Devon Energy",            "ticker": "DVN",  "category": "control"},
    {"cik": "18926",   "firm": "Lumen Technologies",      "ticker": "LUMN", "category": "control"},
    {"cik": "101830",  "firm": "Range Resources",         "ticker": "RRC",  "category": "control"},
    {"cik": "1096752", "firm": "Kohl's",                  "ticker": "KSS",  "category": "control"},
    {"cik": "47111",   "firm": "Avis Budget Group",       "ticker": "CAR",  "category": "control"},
    {"cik": "60440",   "firm": "Williams-Sonoma",         "ticker": "WSM",  "category": "control"},
    {"cik": "40533",   "firm": "Dollar Tree",             "ticker": "DLTR", "category": "control"},
    {"cik": "715787",  "firm": "SM Energy",               "ticker": "SM",   "category": "control"},
    {"cik": "783412",  "firm": "Callon Petroleum",        "ticker": "CPE",  "category": "control"},
    {"cik": "1004440", "firm": "Edison International",    "ticker": "EIX",  "category": "control"},  # re-used after emerged
    {"cik": "1666700", "firm": "Dollar General",          "ticker": "DG",   "category": "control"},
    {"cik": "23217",   "firm": "Macy's",                  "ticker": "M",    "category": "control"},
    {"cik": "1085869", "firm": "Netflix",                 "ticker": "NFLX", "category": "control"},
    {"cik": "109380",  "firm": "Zions Bancorporation",    "ticker": "ZION", "category": "control"},
    {"cik": "49071",   "firm": "Hasbro",                  "ticker": "HAS",  "category": "control"},
    {"cik": "310764",  "firm": "Leggett and Platt",       "ticker": "LEG",  "category": "control"},
    {"cik": "14846",   "firm": "Briggs and Stratton",     "ticker": "BGG",  "category": "control"},  # also distressed 2020 — swap
    {"cik": "726854",  "firm": "Office Depot",            "ticker": "ODP",  "category": "control"},
    {"cik": "1616862", "firm": "Albertsons",              "ticker": "ACI",  "category": "control"},
    {"cik": "68505",   "firm": "Walgreens Boots Alliance","ticker": "WBA",  "category": "control"},
]


# ── Scenario C: Risk Disclosure and the 2023 US Regional Banking Crisis ──────
SCENARIO_C = [
    # Failed banks
    {"cik": "719739",  "firm": "SVB Financial Group",    "ticker": "SIVB", "category": "failed"},
    {"cik": "1288946", "firm": "Signature Bank",         "ticker": "SBNY", "category": "failed"},
    {"cik": "798941",  "firm": "First Republic Bank",    "ticker": "FRC",  "category": "failed"},
    # Stressed survivors
    {"cik": "1212545", "firm": "Western Alliance Bancorporation", "ticker": "WAL", "category": "stressed"},
    {"cik": "1102266", "firm": "PacWest Bancorp",        "ticker": "PACW", "category": "stressed"},
    {"cik": "28412",   "firm": "Comerica",               "ticker": "CMA",  "category": "stressed"},
    {"cik": "109380",  "firm": "Zions Bancorporation",   "ticker": "ZION", "category": "stressed"},
    {"cik": "91576",   "firm": "KeyCorp",                "ticker": "KEY",  "category": "stressed"},
    # Unaffected regional banks
    {"cik": "42682",   "firm": "Glacier Bancorp",        "ticker": "GBCI", "category": "unaffected_regional"},
    {"cik": "70858",   "firm": "Old National Bancorp",   "ticker": "ONB",  "category": "unaffected_regional"},
    {"cik": "1558243", "firm": "Independent Bank Group", "ticker": "IBTX", "category": "unaffected_regional"},
    {"cik": "46619",   "firm": "Heartland Financial USA","ticker": "HTLF", "category": "unaffected_regional"},
    {"cik": "764038",  "firm": "South State Corporation","ticker": "SSB",  "category": "unaffected_regional"},
    {"cik": "1062613", "firm": "TowneBank",              "ticker": "TOWN", "category": "unaffected_regional"},
    {"cik": "203596",  "firm": "WesBanco",               "ticker": "WSBC", "category": "unaffected_regional"},
    {"cik": "715787",  "firm": "Renasant Corporation",   "ticker": "RNST", "category": "unaffected_regional"},
    {"cik": "1108320", "firm": "Glacier Hills Bankshares","ticker": "GHBS","category": "unaffected_regional"},
    {"cik": "883948",  "firm": "Banner Financial Group", "ticker": "BANR", "category": "unaffected_regional"},
    # Large systemic banks
    {"cik": "19617",   "firm": "JPMorgan Chase",         "ticker": "JPM",  "category": "large_systemic"},
    {"cik": "70858",   "firm": "Bank of America",        "ticker": "BAC",  "category": "large_systemic"},
    {"cik": "72971",   "firm": "Citigroup",              "ticker": "C",    "category": "large_systemic"},
    {"cik": "72971",   "firm": "Wells Fargo",            "ticker": "WFC",  "category": "large_systemic"},
    {"cik": "886982",  "firm": "Morgan Stanley",         "ticker": "MS",   "category": "large_systemic"},
    {"cik": "65984",   "firm": "Goldman Sachs",          "ticker": "GS",   "category": "large_systemic"},
    {"cik": "49196",   "firm": "US Bancorp",             "ticker": "USB",  "category": "large_systemic"},
]
YEARS_C = [2020, 2021, 2022]


# ── Scenario D: Supply Chain Risk Before and After COVID-19 2019-2022 ────────
SCENARIO_D = [
    # Automotive
    {"cik": "37996",   "firm": "Ford Motor Company",     "ticker": "F",    "category": "automotive"},
    {"cik": "40987",   "firm": "General Motors",         "ticker": "GM",   "category": "automotive"},
    {"cik": "1318605", "firm": "Tesla",                  "ticker": "TSLA", "category": "automotive"},
    {"cik": "723254",  "firm": "BorgWarner",             "ticker": "BWA",  "category": "automotive"},
    {"cik": "60714",   "firm": "Aptiv",                  "ticker": "APTV", "category": "automotive"},
    # Consumer electronics
    {"cik": "320193",  "firm": "Apple",                  "ticker": "AAPL", "category": "electronics"},
    {"cik": "826083",  "firm": "HP Inc",                 "ticker": "HPQ",  "category": "electronics"},
    {"cik": "217346",  "firm": "Dell Technologies",      "ticker": "DELL", "category": "electronics"},
    {"cik": "1418819", "firm": "Qualcomm",               "ticker": "QCOM", "category": "electronics"},
    {"cik": "1037868", "firm": "Jabil",                  "ticker": "JBL",  "category": "electronics"},
    # Retail (supply-chain intensive)
    {"cik": "104169",  "firm": "Walmart",                "ticker": "WMT",  "category": "retail"},
    {"cik": "27419",   "firm": "Target",                 "ticker": "TGT",  "category": "retail"},
    {"cik": "1018724", "firm": "Amazon",                 "ticker": "AMZN", "category": "retail"},
    {"cik": "354950",  "firm": "Home Depot",             "ticker": "HD",   "category": "retail"},
    {"cik": "764478",  "firm": "Best Buy",               "ticker": "BBY",  "category": "retail"},
    # Industrial manufacturing
    {"cik": "66740",   "firm": "3M",                     "ticker": "MMM",  "category": "industrial"},
    {"cik": "773840",  "firm": "Honeywell",              "ticker": "HON",  "category": "industrial"},
    {"cik": "76334",   "firm": "Parker Hannifin",        "ticker": "PH",   "category": "industrial"},
    {"cik": "49826",   "firm": "Illinois Tool Works",    "ticker": "ITW",  "category": "industrial"},
    {"cik": "1439891", "firm": "Flex Ltd",               "ticker": "FLEX", "category": "industrial"},
    # Logistics
    {"cik": "230568",  "firm": "FedEx",                  "ticker": "FDX",  "category": "logistics"},
    {"cik": "100030",  "firm": "UPS",                    "ticker": "UPS",  "category": "logistics"},
    {"cik": "1054374", "firm": "Expeditors International","ticker": "EXPD","category": "logistics"},
    {"cik": "1166928", "firm": "XPO Logistics",          "ticker": "XPO",  "category": "logistics"},
    {"cik": "813672",  "firm": "Ryder System",           "ticker": "R",    "category": "logistics"},
]
YEARS_D = [2019, 2020, 2021, 2022]


# ---------------------------------------------------------------------------
# EDGAR helpers
# ---------------------------------------------------------------------------

SESSION = requests.Session()
SESSION.headers.update(HEADERS)
_last_request = 0.0


def edgar_get(url: str, retries: int = 3) -> requests.Response:
    """GET with rate-limiting and retry on 5xx / timeout."""
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < RATE_SLEEP:
        time.sleep(RATE_SLEEP - elapsed)
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=30)
            _last_request = time.time()
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 10))
                log.warning("Rate-limited; sleeping %d s", wait)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        except requests.exceptions.Timeout:
            log.warning("Timeout on %s (attempt %d)", url, attempt + 1)
            time.sleep(5)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code < 500:
                raise
            log.warning("HTTP %s on %s (attempt %d)", e.response.status_code, url, attempt + 1)
            time.sleep(5)
    raise RuntimeError(f"Failed after {retries} attempts: {url}")


def get_submissions(cik: str) -> dict:
    url = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
    return edgar_get(url).json()


def find_10k_filings(cik: str, target_fiscal_years: list) -> list:
    """
    Return a list of dicts {accession, filing_date, fiscal_year} for 10-K filings
    whose fiscal year is in target_fiscal_years.
    Checks both the recent filings block and any older-filings JSON files.
    """
    subs = get_submissions(cik)
    results = []
    seen_years = set()

    def _scan_block(block):
        forms      = block.get("form", [])
        dates      = block.get("filingDate", [])
        accessions = block.get("accessionNumber", [])
        periods    = block.get("reportDate", [""] * len(forms))
        for form, date, acc, period in zip(forms, dates, accessions, periods):
            if form not in ("10-K", "10-K/A"):
                continue
            # Determine fiscal year from reportDate when available
            if period and len(period) >= 4:
                fy = int(period[:4])
            else:
                # Fall back: filing in Jan-Apr usually covers prior fiscal year
                filing_year = int(date[:4])
                filing_month = int(date[5:7])
                fy = filing_year - 1 if filing_month <= 4 else filing_year
            if fy in target_fiscal_years and fy not in seen_years:
                seen_years.add(fy)
                results.append({
                    "accession":    acc.replace("-", ""),
                    "filing_date":  date,
                    "fiscal_year":  fy,
                })

    _scan_block(subs.get("filings", {}).get("recent", {}))

    # Older filings are paginated into separate JSON files
    for extra in subs.get("filings", {}).get("files", []):
        if len(seen_years) >= len(target_fiscal_years):
            break
        url = "https://data.sec.gov/submissions/" + extra["name"]
        try:
            extra_data = edgar_get(url).json()
            _scan_block(extra_data)
        except Exception as e:
            log.warning("Could not fetch extra filings page %s: %s", extra["name"], e)

    return results


def get_filing_doc_url(cik: str, accession: str) -> str | None:
    """Return the URL of the primary 10-K HTML/HTM document."""
    acc_fmt = f"{accession[:10]}-{accession[10:12]}-{accession[12:]}"
    idx_url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
               f"{accession}/index.json")
    try:
        idx = edgar_get(idx_url).json()
    except Exception as e:
        log.warning("Cannot fetch filing index %s: %s", acc_fmt, e)
        return None

    items = idx.get("directory", {}).get("item", [])
    # Prefer the document explicitly typed as 10-K
    for item in items:
        if item.get("type") == "10-K" and item["name"].lower().endswith((".htm", ".html")):
            return (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                    f"{accession}/{item['name']}")
    # Fallback: first htm file
    for item in items:
        if item["name"].lower().endswith((".htm", ".html")):
            return (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                    f"{accession}/{item['name']}")
    return None


# ---------------------------------------------------------------------------
# Section extraction patterns
# Each entry: (section_key, start_pattern, end_pattern)
# ---------------------------------------------------------------------------

SECTIONS = [
    (
        "item_1a",
        re.compile(r"item\s+1a[\.\-\s]*risk\s+factors", re.IGNORECASE),
        re.compile(r"item\s+1b[\.\-\s]|item\s+2[\.\-\s]", re.IGNORECASE),
    ),
    (
        "item_7",
        re.compile(
            r"item\s+7[\.\-\s]*management[\'\u2019]?s?\s+discussion\s+and\s+analysis",
            re.IGNORECASE,
        ),
        re.compile(r"item\s+7a[\.\-\s]|item\s+8[\.\-\s]", re.IGNORECASE),
    ),
    (
        "item_7a",
        re.compile(
            r"item\s+7a[\.\-\s]*quantitative\s+and\s+qualitative\s+disclosures",
            re.IGNORECASE,
        ),
        re.compile(r"item\s+8[\.\-\s]", re.IGNORECASE),
    ),
]


def _html_to_text(html_bytes: bytes) -> str:
    """Convert 10-K HTML to plain text with normalised whitespace."""
    soup = BeautifulSoup(html_bytes, "lxml")
    for tag in soup.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def extract_section(text: str, start_pat: re.Pattern, end_pat: re.Pattern) -> str | None:
    """
    Extract text between start_pat and end_pat.
    Returns cleaned body string, or None if start not found or body too short.
    The function searches for the *second* occurrence of start_pat when the
    first match falls inside a table of contents (i.e., is very short).
    """
    pos = 0
    for _ in range(3):          # try up to 3 occurrences of the start marker
        m_start = start_pat.search(text, pos)
        if not m_start:
            return None
        tail = text[m_start.end():]
        m_end = end_pat.search(tail)
        body = tail[: m_end.start()] if m_end else tail[:500_000]
        body = re.sub(r"\s+", " ", body).strip()
        if len(body) > 500:     # long enough to be a real section, not a TOC entry
            return body
        pos = m_start.end()     # advance and try the next occurrence
    return None


def download_sections(firm: dict, fiscal_year: int, filing: dict) -> list[dict]:
    """
    Download one 10-K filing and extract all three sections.
    Returns a list of row dicts (one per section found); may be empty.
    """
    cik = firm["cik"]
    acc = filing["accession"]

    doc_url = get_filing_doc_url(cik, acc)
    if not doc_url:
        log.warning("  No document URL: %s %s FY%d", firm["firm"], acc, fiscal_year)
        return []

    try:
        resp = edgar_get(doc_url)
    except Exception as e:
        log.warning("  Download failed: %s %s: %s", firm["firm"], acc, e)
        return []

    text = _html_to_text(resp.content)
    base = {k: firm.get(k, "") for k in ("cik", "firm", "ticker", "category")}
    base.update({
        "year":             fiscal_year,
        "filing_date":      filing["filing_date"],
        "accession_number": f"{acc[:10]}-{acc[10:12]}-{acc[12:]}",
    })
    if "bk_year" in firm:
        base["bk_year"] = firm["bk_year"]

    rows = []
    for section_key, start_pat, end_pat in SECTIONS:
        body = extract_section(text, start_pat, end_pat)
        if body:
            row = dict(base)
            row["section"]   = section_key
            row["text"]      = body
            row["word_count"] = len(body.split())
            rows.append(row)
            log.info("  %s FY%d  %s  %d words",
                     firm["firm"], fiscal_year, section_key, row["word_count"])
        else:
            log.warning("  %s FY%d  %s  NOT FOUND",
                        firm["firm"], fiscal_year, section_key)

    return rows


# ---------------------------------------------------------------------------
# Scenario builders
# ---------------------------------------------------------------------------

COLUMNS = ["cik", "firm", "ticker", "category", "year", "section",
           "filing_date", "accession_number", "text", "word_count"]


def build_scenario(label: str, firms: list, target_years_fn,
                   out_dir: Path) -> None:
    """
    Download filings for all firms and write corpus.csv.
    Each row is one (firm, year, section) combination.
    Sections collected: item_1a, item_7, item_7a.

    target_years_fn: callable(firm) -> list[int]
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "corpus.csv"

    # Resume from existing file if present
    # done_keys tracks (cik, year) pairs — if a filing was attempted we skip it
    # regardless of which sections were found (avoids re-downloading)
    done_keys: set[tuple] = set()
    rows: list[dict] = []
    if out_path.exists():
        existing = pd.read_csv(out_path, dtype=str)
        rows = existing.to_dict("records")
        done_keys = {(r["cik"], str(r["year"])) for r in rows}
        log.info("Resuming Scenario %s: %d rows already saved", label, len(rows))

    total_firms = len(firms)
    for i, firm in enumerate(firms, 1):
        cik  = firm["cik"]
        name = firm["firm"]
        target_years = target_years_fn(firm)

        log.info("[%s] %d/%d  %s (CIK %s)  years=%s",
                 label, i, total_firms, name, cik, target_years)

        try:
            filings = find_10k_filings(cik, target_years)
        except Exception as e:
            log.error("  Cannot get submissions for %s: %s", name, e)
            continue

        if not filings:
            log.warning("  No 10-K filings found for %s in %s", name, target_years)
            continue

        for filing in filings:
            fy  = filing["fiscal_year"]
            key = (cik, str(fy))
            if key in done_keys:
                log.info("  Skipping %s FY%d (already saved)", name, fy)
                continue

            new_rows = download_sections(firm, fy, filing)
            rows.extend(new_rows)
            done_keys.add(key)   # mark as attempted even if 0 sections found

        # Write after each firm so progress is not lost on interruption
        if rows:
            pd.DataFrame(rows).to_csv(out_path, index=False)

    # Final write with consistent column order
    if rows:
        df = pd.DataFrame(rows)
        extra_cols = [c for c in df.columns if c not in COLUMNS]
        df[COLUMNS + extra_cols].to_csv(out_path, index=False)
        log.info("Scenario %s complete: %d rows -> %s", label, len(df), out_path)
    else:
        log.error("Scenario %s: no rows collected", label)


# ---------------------------------------------------------------------------
# Target-year helpers
# ---------------------------------------------------------------------------

def years_a(firm):
    return YEARS_A

def years_b(firm):
    if firm["category"] == "distressed":
        bk = firm.get("bk_year", 2020)
        return [bk - 3, bk - 2, bk - 1]
    else:
        # Controls: cover 2015-2023 broadly; we'll slice to 3 filings post-build
        return [2016, 2017, 2018, 2019, 2020, 2021, 2022]

def years_c(firm):
    return YEARS_C

def years_d(firm):
    return YEARS_D


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build AG952 assignment corpora from EDGAR")
    parser.add_argument("--scenario", choices=["A", "B", "C", "D", "all"],
                        default="all", help="Which scenario to build (default: all)")
    args = parser.parse_args()

    scenarios = {
        "A": (SCENARIO_A, years_a, DATA_ROOT / "scenario_a"),
        "B": (SCENARIO_B, years_b, DATA_ROOT / "scenario_b"),
        "C": (SCENARIO_C, years_c, DATA_ROOT / "scenario_c"),
        "D": (SCENARIO_D, years_d, DATA_ROOT / "scenario_d"),
    }

    to_run = ["A", "B", "C", "D"] if args.scenario == "all" else [args.scenario]

    for key in to_run:
        firms, year_fn, out_dir = scenarios[key]
        log.info("=" * 60)
        log.info("Starting Scenario %s  (%d firms)", key, len(firms))
        log.info("=" * 60)
        build_scenario(key, firms, year_fn, out_dir)

    log.info("All done. Output files:")
    for key in to_run:
        p = scenarios[key][2] / "corpus.csv"
        if p.exists():
            df = pd.read_csv(p)
            log.info("  scenario_%s/corpus.csv  %d rows", key.lower(), len(df))
        else:
            log.warning("  scenario_%s/corpus.csv  NOT FOUND", key.lower())
