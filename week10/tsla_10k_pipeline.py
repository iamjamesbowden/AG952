#!/usr/bin/env python3
"""
TSLA 10-K Image and Data Extraction Pipeline
AG952 Text Analytics — Session 3, Steps 1–7

Steps:
  1. Locate 10-K filings via SEC EDGAR (FY2020–2023)
  2. Extract images from each 10-K HTML document
  3. Filter images (size, aspect, excluded text/filename)
  4. Classify images (type, data content, section)
  5. Extract GAAP metrics (revenue, net income, operating income, gross margin %, EPS)
  6. Extract non-financial KPIs (deliveries, production, energy, Superchargers, solar)
  7. Print summary report

Outputs → workshop_data/ and Google Drive folder 1Nf0X7aCBce8knRfyN7N-B1ErSoioxj7N
"""

import os, re, time, json, logging, base64, urllib.parse, subprocess, warnings
from pathlib import Path
from io import BytesIO, StringIO

import requests
import pandas as pd
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from PIL import Image, UnidentifiedImageError

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

WORKSHOP       = Path("/Users/jamesbowden/Library/CloudStorage/"
                      "OneDrive-UniversityofStrathclyde/Research/"
                      "GBF Paper/workshop_data")
IMG_BASE       = WORKSHOP / "images"
HTML_CACHE     = WORKSHOP / "html_cache"
DRIVE_FOLDER   = "1Nf0X7aCBce8knRfyN7N-B1ErSoioxj7N"
TESLA_CIK      = "1318605"
TARGET_FY      = [2020, 2021, 2022, 2023]
DELAY          = 0.2   # stay well under SEC's 10 req/s limit

SEC_HEADERS = {
    "User-Agent": "University of Strathclyde AG952 Research jamesbowden@strath.ac.uk",
    "Accept-Encoding": "gzip, deflate",
}

for d in [WORKSHOP, IMG_BASE, HTML_CACHE]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(WORKSHOP / "session3_pipeline.log", mode="w"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# UTILITY — cached HTML download
# ══════════════════════════════════════════════════════════════════════════════

def _get_html(fy: int, doc_url: str) -> str:
    """Download and cache 10-K HTML (large files: 30–80 MB)."""
    cache_path = HTML_CACHE / f"tsla_{fy}_10k.html"
    if cache_path.exists():
        log.info(f"FY{fy}: loading HTML from cache ({cache_path.stat().st_size/1e6:.1f} MB)")
        return cache_path.read_text(encoding="utf-8", errors="replace")

    log.info(f"FY{fy}: downloading HTML → {doc_url}")
    time.sleep(DELAY)
    r = requests.get(doc_url, headers=SEC_HEADERS, timeout=180, stream=True)
    r.raise_for_status()

    chunks = []
    for chunk in r.iter_content(chunk_size=131_072):
        chunks.append(chunk)
    raw = b"".join(chunks)
    html = raw.decode("utf-8", errors="replace")
    cache_path.write_text(html, encoding="utf-8")
    log.info(f"FY{fy}: cached {len(html)/1e6:.1f} MB")
    return html


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Locate 10-K filings via SEC EDGAR
# ══════════════════════════════════════════════════════════════════════════════

def step1_get_filings() -> dict:
    """Return {fy: {accession, filing_date, primary_doc, doc_url, base_url}}."""
    log.info("═"*60)
    log.info("STEP 1 — Locating Tesla 10-K filings (FY2020–2023)")
    log.info("═"*60)

    cik_padded = TESLA_CIK.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    log.info(f"Fetching submissions: {url}")
    time.sleep(DELAY)
    r = requests.get(url, headers=SEC_HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()

    results = {}

    def _scan_batch(batch: dict):
        for acc, date, form, pdoc in zip(
            batch["accessionNumber"],
            batch["filingDate"],
            batch["form"],
            batch["primaryDocument"],
        ):
            if form != "10-K":
                continue
            fy = int(date[:4]) - 1   # filed in year N → covers fiscal year N-1
            if fy not in TARGET_FY or fy in results:
                continue
            acc_nodash = acc.replace("-", "")
            base_url   = f"https://www.sec.gov/Archives/edgar/data/{TESLA_CIK}/{acc_nodash}"
            results[fy] = {
                "accession":   acc,
                "acc_nodash":  acc_nodash,
                "filing_date": date,
                "primary_doc": pdoc,
                "doc_url":     f"{base_url}/{pdoc}",
                "base_url":    base_url,
            }
            log.info(f"  FY{fy}: {acc}  ({pdoc})  filed {date}")

    _scan_batch(data["filings"]["recent"])

    # If any FY not found in the "recent" batch, fetch older submission pages
    if len(results) < len(TARGET_FY):
        for file_info in data["filings"].get("files", []):
            if len(results) == len(TARGET_FY):
                break
            batch_url = f"https://data.sec.gov/submissions/{file_info['name']}"
            log.info(f"  Fetching older batch: {batch_url}")
            time.sleep(DELAY)
            rb = requests.get(batch_url, headers=SEC_HEADERS, timeout=30)
            if rb.status_code == 200:
                _scan_batch(rb.json())

    missing = [fy for fy in TARGET_FY if fy not in results]
    if missing:
        log.warning(f"Could not locate 10-K filings for: FY{missing}")

    log.info(f"Located {len(results)} filings: {sorted(results)}")
    return results


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Extract images from each 10-K HTML document
# ══════════════════════════════════════════════════════════════════════════════

def _context(tag, n: int = 100) -> tuple[str, str, str]:
    """Return (section_heading, prev_N_words, next_N_words) for an img tag."""
    # Nearest preceding heading
    heading = ""
    for h in tag.find_all_previous(["h1", "h2", "h3", "h4"], limit=3):
        text = h.get_text(" ", strip=True)
        if text:
            heading = text[:200]
            break

    # Walk backwards collecting text
    prev_words = []
    for node in tag.find_all_previous(string=True):
        t = node.strip()
        if t:
            prev_words = t.split() + prev_words
        if len(prev_words) >= n:
            break
    prev_text = " ".join(prev_words[-n:])

    # Walk forwards
    next_words = []
    for node in tag.find_all_next(string=True):
        t = node.strip()
        if t:
            next_words.extend(t.split())
        if len(next_words) >= n:
            break
    next_text = " ".join(next_words[:n])

    return heading, prev_text, next_text


def _download_img(src: str, base_url: str, session: requests.Session) -> bytes | None:
    """Fetch image bytes from data URI, relative path, or absolute URL."""
    if src.startswith("data:image"):
        try:
            _, b64 = src.split(",", 1)
            return base64.b64decode(b64)
        except Exception:
            return None

    if not src.startswith("http"):
        src = urllib.parse.urljoin(base_url + "/", src)

    # Skip XBRL viewer references (R[n].htm pattern)
    if re.search(r"/R\d+\.htm", src, re.I):
        return None

    try:
        time.sleep(DELAY)
        r = session.get(src, headers=SEC_HEADERS, timeout=30)
        return r.content if r.status_code == 200 else None
    except Exception as e:
        log.debug(f"  img fetch failed {src}: {e}")
        return None


def step2_extract_images(fy: int, filing: dict) -> list[dict]:
    """Download 10-K HTML, parse <img> tags, save as PNG, record context."""
    log.info("═"*60)
    log.info(f"STEP 2 — Extracting images from FY{fy}")
    log.info("═"*60)

    out_dir = IMG_BASE / f"TSLA_{fy}"
    out_dir.mkdir(parents=True, exist_ok=True)

    html = _get_html(fy, filing["doc_url"])
    soup = BeautifulSoup(html, "lxml")
    img_tags = soup.find_all("img")
    log.info(f"FY{fy}: found {len(img_tags)} <img> tags")

    session = requests.Session()
    records = []

    for n, tag in enumerate(img_tags, 1):
        src = (tag.get("src") or tag.get("data-src") or "").strip()
        if not src:
            continue

        heading, prev_ctx, next_ctx = _context(tag)
        img_bytes = _download_img(src, filing["base_url"], session)

        if not img_bytes:
            log.debug(f"  FY{fy} img_{n:03d}: no bytes ({src[:80]})")
            continue

        local_path = out_dir / f"img_{n:03d}.png"
        try:
            img = Image.open(BytesIO(img_bytes))
            img.save(local_path, "PNG")
            width, height = img.size
        except (UnidentifiedImageError, Exception) as e:
            log.debug(f"  FY{fy} img_{n:03d}: save error: {e}")
            continue

        records.append({
            "fy":              fy,
            "img_index":       n,
            "src":             src[:200],
            "local_path":      str(local_path),
            "width":           width,
            "height":          height,
            "section_heading": heading,
            "prev_context":    prev_ctx,
            "next_context":    next_ctx,
        })
        log.info(f"  FY{fy} img_{n:03d}: {width}×{height}  {src[:60]}")

    log.info(f"FY{fy}: extracted {len(records)} images")
    return records


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Filter images
# ══════════════════════════════════════════════════════════════════════════════

EXCLUDE_CTX_PHRASES  = ["stock performance", "comparison of cumulative"]
EXCLUDE_SRC_KEYWORDS = ["logo", "signature"]

def step3_filter(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (retained, excluded). excluded records gain 'exclusion_reason'."""
    log.info("═"*60)
    log.info("STEP 3 — Filtering images")
    log.info("═"*60)

    retained, excluded = [], []
    for rec in records:
        w, h = rec["width"], rec["height"]
        reason = None

        if w < 100 or h < 100:
            reason = f"too small ({w}×{h})"
        elif w / max(h, 1) < 0.2:
            reason = f"aspect ratio too narrow ({w/max(h,1):.2f})"
        else:
            ctx  = (rec["prev_context"] + " " + rec["next_context"]).lower()
            src  = rec["src"].lower()
            for phrase in EXCLUDE_CTX_PHRASES:
                if phrase in ctx:
                    reason = f"excluded context phrase: '{phrase}'"
                    break
            if reason is None:
                for kw in EXCLUDE_SRC_KEYWORDS:
                    if kw in src:
                        reason = f"excluded src keyword: '{kw}'"
                        break

        if reason:
            rec["exclusion_reason"] = reason
            excluded.append(rec)
            log.info(f"  EXCL FY{rec['fy']} img_{rec['img_index']:03d}: {reason}")
        else:
            retained.append(rec)

    log.info(f"Filter: {len(retained)} retained / {len(excluded)} excluded "
             f"(total {len(records)})")
    return retained, excluded


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Classify images
# ══════════════════════════════════════════════════════════════════════════════

_TYPE_RULES = [
    ("bar chart",          r"\bbar\s+(?:chart|graph)\b|\bcolumn\s+chart\b|\bhistogram\b"),
    ("line graph",         r"\bline\s+(?:graph|chart)\b|\btrend(?:line)?\b"),
    ("pie chart",          r"\bpie\s+chart\b|\bdoughnut\b"),
    ("map",                r"\bgigafactory\b|\bfacility\b|\bgeograph\b|\bworld\s+map\b|\blocation\b"),
    ("process/flow diagram",r"\bprocess\b|\bflow\b|\bworkflow\b|\bvalue\s+chain\b|\bsupply\s+chain\b"),
    ("strategy diagram",   r"\bstrateg\b|\bvision\b|\bmission\b|\bpillar\b|\broadmap\b|\binitiative\b"),
    ("table",              r"\btable\b|\bschedule\b|\bsummar[yi]\b"),
    ("photo",              r"\bphoto\b|\bimage\s+of\b|\bvehicle\b|\bcar\b|\bfactory\b|"
                           r"\bpowerwall\b|\bmegapack\b|\bsolar\b|\bpanel\b|\bcharger\b"),
]

_CONTENT_RULES = [
    ("GAAP",          r"\btotal\s+(?:net\s+)?revenues?\b|\bnet\s+income\b|\beps\b|"
                      r"\bearnings\s+per\s+share\b|\bgross\s+profit\b|\bgaap\b|"
                      r"\boperating\s+(?:income|loss)\b|\bgross\s+margin\b"),
    ("non-GAAP",      r"\bnon.gaap\b|\badjusted\b|\bebitda\b"),
    ("financial KPI", r"\bfree\s+cash\s+flow\b|\bcapex\b|\bcapital\s+expenditure\b|"
                      r"\bcash\s+(?:and\s+cash\s+equivalents)?\b|\bdebt\b|\bleverage\b"),
    ("non-financial KPI", r"\bdeliveries?\b|\bproduction\b|\bsupercharger\b|"
                          r"\benergy\s+(?:storage\s+)?deployed\b|\bgwh\b|\bvehicle\b|"
                          r"\bmodel\s+[sxy3]\b|\bmegapack\b|\bpowerwall\b|\binstall\b"),
    ("macro",         r"\bev\s+market\b|\belectric\s+vehicle\s+market\b|\bclimate\b|"
                      r"\bcarbon\b|\bindustry\s+trend\b"),
]

def step4_classify(records: list[dict]) -> list[dict]:
    """Add image_type, data_content, section, is_ambiguous to each record."""
    log.info("═"*60)
    log.info("STEP 4 — Classifying images")
    log.info("═"*60)

    for rec in records:
        ctx = " ".join([rec["section_heading"], rec["prev_context"],
                        rec["next_context"]]).lower()

        # Image type
        img_type = "other"
        for label, pat in _TYPE_RULES:
            if re.search(pat, ctx, re.I):
                img_type = label
                break

        # Data content — collect all matches
        matches = [lbl for lbl, pat in _CONTENT_RULES if re.search(pat, ctx, re.I)]
        if not matches:
            data_content = "qualitative"
        elif len(matches) == 1:
            data_content = matches[0]
        else:
            data_content = " / ".join(matches)

        # Ambiguity: type unknown, or GAAP+non-GAAP both hit, or qualitative on non-photo
        is_ambiguous = (
            img_type == "other"
            or ("GAAP" in data_content and "non-GAAP" in data_content)
            or (data_content == "qualitative" and img_type not in ("photo",))
        )

        rec["image_type"]    = img_type
        rec["data_content"]  = data_content
        rec["section"]       = rec["section_heading"][:100]
        rec["is_ambiguous"]  = is_ambiguous

        log.info(f"  FY{rec['fy']} img_{rec['img_index']:03d}: "
                 f"{img_type} | {data_content} | ambig={is_ambiguous}")

    return records


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — GAAP metrics extraction
# ══════════════════════════════════════════════════════════════════════════════

_GAAP_ROWS = {
    "total_revenue":    r"total\s+(?:net\s+)?revenues?",
    "gross_profit":     r"gross\s+profit",
    "operating_income": r"(?:income|loss)\s+from\s+operations|operating\s+(?:income|loss)",
    "net_income":       r"net\s+income(?:\s*\(loss\))?(?:\s+attributable\b)?",
    # Tesla: "Net income per share of common stock attributable...— Basic" / "— Diluted"
    "eps_basic":        r"(?:net\s+income|earnings)\s+per\s+(?:share|common).{0,80}—?\s*basic"
                        r"|basic\s+(?:net\s+income|earnings)\s+per\s+(?:share|common)",
    "eps_diluted":      r"(?:net\s+income|earnings)\s+per\s+(?:share|common).{0,80}—?\s*diluted"
                        r"|diluted\s+(?:net\s+income|earnings)\s+per\s+(?:share|common)",
}

def _parse_num(s: str) -> float | None:
    s = s.strip().replace(",", "").replace("$", "").replace("\xa0", "").replace(" ", "")
    if s in ("", "—", "–", "-", "N/A", "nm", "*"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        v = float(s)
        return -v if neg else v
    except ValueError:
        return None


def _extract_gaap(html: str, fy: int) -> dict:
    """Identify the Consolidated Statement of Operations table, then extract metrics.
    Using a table-scoped approach avoids picking up stray values from earlier MD&A tables."""
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    log.info(f"  FY{fy}: scanning {len(tables)} tables for income statement")

    metrics = {k: None for k in _GAAP_ROWS}

    # Score each table by how many IS row-label patterns it matches.
    # Tiebreak by total-revenue value: annual > quarterly, so highest revenue wins.
    candidates = []
    for table in tables:
        rows = table.find_all("tr")
        labels = []
        for r in rows:
            cells = r.find_all(["td", "th"])
            if cells:
                labels.append(cells[0].get_text(" ", strip=True))
        score = sum(
            1 for pat in _GAAP_ROWS.values()
            if any(re.search(pat, lbl, re.I) for lbl in labels)
        )
        if score < 2:
            continue
        # Extract the revenue value from this table for tiebreaking
        revenue = 0.0
        for r in rows:
            cells = r.find_all(["td", "th"])
            if not cells:
                continue
            if re.search(r"total\s+(?:net\s+)?revenues?", cells[0].get_text(" ", strip=True), re.I):
                nums = [n for n in (_parse_num(c.get_text(strip=True)) for c in cells[1:])
                        if n is not None and n > 0]
                if nums:
                    revenue = nums[0]
                    break
        candidates.append((score, revenue, table))

    if not candidates:
        log.warning(f"  FY{fy}: could not identify income statement table")
        return metrics

    # Sort: highest total revenue first (annual > any quarterly/segment table),
    # then break ties by IS-metric score.
    candidates.sort(key=lambda x: (x[1], x[0]), reverse=True)
    best_score, best_rev, best_table = candidates[0]
    log.info(f"  FY{fy}: income statement table identified "
             f"(score {best_score}, total_revenue {best_rev:,.0f}M)")

    # Extract from the identified table only
    for row in best_table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        row_text = cells[0].get_text(" ", strip=True)
        for metric, pat in _GAAP_ROWS.items():
            if metrics[metric] is not None:
                continue
            if re.search(pat, row_text, re.I):
                nums = [n for n in (_parse_num(c.get_text(strip=True)) for c in cells[1:])
                        if n is not None]
                if nums:
                    # For EPS: reject values > 100 (those are share-count rows, not per-share)
                    if "eps" in metric and nums[0] > 100:
                        continue
                    metrics[metric] = nums[0]
                    log.info(f"  FY{fy} {metric}: {nums[0]:,.3f}M")

    return metrics


def step5_gaap_metrics(filings: dict) -> pd.DataFrame:
    """Extract GAAP metrics for each FY. Returns DataFrame (values in $M)."""
    log.info("═"*60)
    log.info("STEP 5 — Extracting GAAP metrics")
    log.info("═"*60)

    rows = []
    for fy in sorted(filings):
        log.info(f"FY{fy}: extracting GAAP metrics")
        html = _get_html(fy, filings[fy]["doc_url"])
        m = _extract_gaap(html, fy)
        m["fy"] = fy
        m["units"] = "USD millions"

        # Gross margin %
        if m["total_revenue"] and m["gross_profit"]:
            m["gross_margin_pct"] = round(100 * m["gross_profit"] / m["total_revenue"], 2)
        else:
            m["gross_margin_pct"] = None

        rows.append(m)

    df = pd.DataFrame(rows).sort_values("fy").reset_index(drop=True)

    # YoY % change
    for col in ["total_revenue", "net_income", "operating_income",
                "gross_margin_pct", "eps_diluted"]:
        if col in df.columns:
            df[f"{col}_yoy_pct"] = df[col].pct_change(fill_method=None).mul(100).round(1)

    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Non-financial KPI extraction
# ══════════════════════════════════════════════════════════════════════════════

_KPI_PATTERNS = {
    # vehicle deliveries — "delivered 1,808,581 consumer vehicles" (FY2022+) or
    # "delivered 499,647 vehicles" (FY2020/2021)
    "vehicle_deliveries": [
        r"delivered\s+([\d,]+)\s+(?:\w+\s+)?vehicles?",
        r"total\s+(?:vehicle\s+)?deliveries\s+of\s+([\d,]+)",
        r"vehicle\s+deliveries\s+(?:of\s+|were\s+|totaled?\s+)([\d,]+)",
        r"([\d,]+)\s+vehicles?\s+(?:were\s+)?delivered",
    ],
    "vehicle_production": [
        r"produced\s+([\d,]+)\s+(?:\w+\s+)?vehicles?",
        r"total\s+(?:vehicle\s+)?production\s+of\s+([\d,]+)",
        r"vehicle\s+production\s+(?:of\s+|was\s+|totaled?\s+)([\d,]+)",
        r"([\d,]+)\s+vehicles?\s+(?:were\s+)?produced",
    ],
    "energy_storage_gwh": [
        r"deployed\s+([\d,.]+)\s*gwh\s+of\s+energy\s+storage",
        r"energy\s+storage\s+(?:products?\s+)?deployed\s*[:\s]*([\d,.]+)\s*gwh",
        r"([\d,.]+)\s*gwh\s+of\s+energy\s+storage",
        r"([\d,.]+)\s*gwh\s+deployed",
    ],
    # Supercharger counts not disclosed as specific numbers in 10-K narrative text;
    # patterns retained for completeness but will return None
    "supercharger_stations": [
        r"([\d,]+)\s+supercharger\s+stations?",
        r"supercharger\s+stations?\s*[:\s]*([\d,]+)",
        r"supercharger\s+network\s+(?:of\s+|with\s+|had\s+|has\s+)([\d,]+)\s+stations?",
        r"operated\s+([\d,]+)\s+supercharger",
    ],
    "supercharger_connectors": [
        r"([\d,]+)\s+supercharger\s+connectors?",
        r"supercharger\s+connectors?\s*[:\s]*([\d,]+)",
        r"([\d,]+)\s+(?:supercharging\s+)?connectors?",
    ],
    # Solar: Tesla reports in same sentence as energy storage GWh
    # "deployed X GWh of energy storage products and Y megawatts of solar energy systems"
    "solar_deployed_mw": [
        r"deployed\s+[\d,.]+\s*gwh\s+of\s+energy\s+storage\s+products?\s+and\s+([\d,.]+)\s+megawatts?",
        r"deployed\s+([\d,]+)\s*mw\s+of\s+solar",
        r"solar\s+(?:energy\s+)?(?:panels?\s+)?deployed\s*[:\s]*([\d,]+)\s*(?:mw|megawatts?)",
        r"([\d,]+)\s*(?:mw|megawatts?)\s+of\s+solar",
    ],
}


def step6_nonfin_kpis(filings: dict) -> pd.DataFrame:
    """Extract non-financial KPIs from narrative text. Returns DataFrame."""
    log.info("═"*60)
    log.info("STEP 6 — Extracting non-financial KPIs")
    log.info("═"*60)

    rows = []
    for fy in sorted(filings):
        log.info(f"FY{fy}: extracting non-financial KPIs")
        html = _get_html(fy, filings[fy]["doc_url"])

        soup = BeautifulSoup(html, "lxml")
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).lower()

        row = {"fy": fy}
        for kpi, patterns in _KPI_PATTERNS.items():
            val = None
            for pat in patterns:
                m = re.search(pat, text, re.I)
                if m:
                    try:
                        val = float(m.group(1).replace(",", ""))
                        log.info(f"  FY{fy} {kpi}: {val:,.1f}  (pattern: {pat[:50]})")
                        break
                    except (ValueError, IndexError):
                        pass
            if val is None:
                log.warning(f"  FY{fy} {kpi}: NOT FOUND")
            row[kpi] = val

        rows.append(row)

    df = pd.DataFrame(rows).sort_values("fy").reset_index(drop=True)

    # YoY % change
    for col in [c for c in df.columns if c != "fy"]:
        df[f"{col}_yoy_pct"] = df[col].pct_change(fill_method=None).mul(100).round(1)

    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Summary report
# ══════════════════════════════════════════════════════════════════════════════

def step7_summary(retained: list[dict], excluded: list[dict],
                  gaap_df: pd.DataFrame, kpi_df: pd.DataFrame):
    """Print summary report to screen."""
    bar = "═" * 70

    print(f"\n{bar}")
    print("TSLA 10-K IMAGE & DATA EXTRACTION — SUMMARY REPORT")
    print(bar)

    for fy in TARGET_FY:
        fy_ret = [r for r in retained if r["fy"] == fy]
        fy_exc = [r for r in excluded  if r["fy"] == fy]
        print(f"\n── FY{fy} {'─'*55}")
        print(f"  Images retained: {len(fy_ret)}   excluded: {len(fy_exc)}")

        if fy_ret:
            tc = pd.Series([r["image_type"]   for r in fy_ret]).value_counts()
            cc = pd.Series([r["data_content"] for r in fy_ret]).value_counts()
            print("  By image type:")
            for t, c in tc.items():
                print(f"    {t:<35} {c}")
            print("  By data content:")
            for c, n in cc.items():
                print(f"    {c:<35} {n}")

        if not kpi_df.empty:
            fy_row = kpi_df[kpi_df["fy"] == fy]
            if not fy_row.empty:
                kpi_base = [c for c in kpi_df.columns if c != "fy" and not c.endswith("_yoy_pct")]
                # rank KPIs by infographic mention count
                mentions = {}
                for kpi in kpi_base:
                    kw = kpi.split("_")[0]
                    mentions[kpi] = sum(
                        1 for r in fy_ret
                        if kw in (r["prev_context"] + r["next_context"]).lower()
                    )
                top5 = sorted(mentions.items(), key=lambda x: x[1], reverse=True)[:5]
                print("  Top 5 non-financial KPIs by infographic mentions:")
                for kpi, cnt in top5:
                    v = fy_row[kpi].values[0] if kpi in fy_row.columns else "N/A"
                    v_str = f"{v:,.1f}" if isinstance(v, float) else str(v)
                    print(f"    {kpi:<35} imgs: {cnt}  value: {v_str}")

    print(f"\n── GAAP Metrics {'─'*52}")
    if not gaap_df.empty:
        show_cols = ["fy", "total_revenue", "gross_profit", "operating_income",
                     "net_income", "gross_margin_pct", "eps_diluted",
                     "total_revenue_yoy_pct", "net_income_yoy_pct"]
        print(gaap_df[[c for c in show_cols if c in gaap_df.columns]].to_string(index=False))

    print(f"\n── Non-Financial KPIs {'─'*47}")
    if not kpi_df.empty:
        base_cols = ["fy"] + [c for c in kpi_df.columns
                              if not c.endswith("_yoy_pct") and c != "fy"]
        print(kpi_df[[c for c in base_cols if c in kpi_df.columns]].to_string(index=False))

    print(f"\n{bar}\n")


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE DRIVE UPLOAD
# ══════════════════════════════════════════════════════════════════════════════

def upload_to_drive():
    log.info("Uploading outputs to Google Drive...")

    # CSV files → root of workshop_data folder
    csv_files = [
        WORKSHOP / "TSLA_gaap_metrics.csv",
        WORKSHOP / "TSLA_nonfin_kpis.csv",
        WORKSHOP / "TSLA_image_exclusions.csv",
        WORKSHOP / "session3_pipeline.log",
    ] + list(WORKSHOP.glob("TSLA_*_image_manifest.csv"))

    for f in csv_files:
        if not f.exists():
            continue
        cmd = ["rclone", "copy", str(f), "gdrive:",
               "--drive-root-folder-id", DRIVE_FOLDER, "--stats-one-line"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            log.info(f"  Uploaded {f.name}")
        else:
            log.warning(f"  Failed {f.name}: {res.stderr[:200]}")

    # Images → images/ subfolder
    cmd = ["rclone", "copy", str(IMG_BASE), "gdrive:images",
           "--drive-root-folder-id", DRIVE_FOLDER,
           "--include", "*.png", "--stats-one-line"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if res.returncode == 0:
        log.info("  Images uploaded")
    else:
        log.warning(f"  Image upload warning: {res.stderr[:200]}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    log.info("TSLA 10-K Pipeline starting")

    # Step 1
    filings = step1_get_filings()
    if not filings:
        log.error("No filings found — aborting")
        return

    # Steps 2–4: image extraction, filtering, classification
    all_records = []
    for fy in sorted(filings):
        records = step2_extract_images(fy, filings[fy])
        all_records.extend(records)

    retained, excluded = step3_filter(all_records)
    retained = step4_classify(retained)

    # Save per-year manifests
    for fy in TARGET_FY:
        fy_rows = [r for r in retained if r["fy"] == fy]
        if fy_rows:
            path = WORKSHOP / f"TSLA_{fy}_image_manifest.csv"
            pd.DataFrame(fy_rows).to_csv(path, index=False)
            log.info(f"Saved {path.name} ({len(fy_rows)} rows)")

    # Save exclusion log
    if excluded:
        excl_path = WORKSHOP / "TSLA_image_exclusions.csv"
        pd.DataFrame(excluded).to_csv(excl_path, index=False)
        log.info(f"Saved TSLA_image_exclusions.csv ({len(excluded)} rows)")

    # Step 5
    gaap_df = step5_gaap_metrics(filings)
    if not gaap_df.empty:
        gaap_path = WORKSHOP / "TSLA_gaap_metrics.csv"
        gaap_df.to_csv(gaap_path, index=False)
        log.info(f"Saved TSLA_gaap_metrics.csv")

    # Step 6
    kpi_df = step6_nonfin_kpis(filings)
    if not kpi_df.empty:
        kpi_path = WORKSHOP / "TSLA_nonfin_kpis.csv"
        kpi_df.to_csv(kpi_path, index=False)
        log.info(f"Saved TSLA_nonfin_kpis.csv")

    # Step 7
    step7_summary(retained, excluded, gaap_df, kpi_df)

    # Upload to Google Drive
    upload_to_drive()

    log.info("Pipeline complete.")


if __name__ == "__main__":
    main()
