"""
TSLA Event Study
- Download TSLA + ^GSPC daily adjusted closing prices
- Compute per-call returns around 17 earnings call dates
- Save TSLA_returns_by_call.csv
- Plot TSLA_price_timeline.png
- Upload both to Google Drive
"""

import json
import re
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import pandas as pd
import yfinance as yf

# ── Paths ────────────────────────────────────────────────────────────────────
TRANSCRIPT_DIR = Path(
    "/Users/jamesbowden/Library/CloudStorage/"
    "OneDrive-UniversityofStrathclyde/Research/GBF Paper/tsla_transcripts_json"
)
OUT_DIR = Path("/tmp/AG952/week10")
DRIVE_FOLDER = "1Nf0X7aCBce8knRfyN7N-B1ErSoioxj7N"

# ── 1. Load call dates from transcript JSONs ─────────────────────────────────
calls = []
for f in sorted(TRANSCRIPT_DIR.glob("*.json")):
    with open(f) as fh:
        data = json.load(fh)
    dt = pd.Timestamp(data["time"])
    year = int(data["year"])
    quarter = int(data["quarter"])
    label = f"{year}Q{quarter}" if quarter > 0 else f"{year}Q0(ASM)"
    calls.append({"label": label, "date": dt.normalize(), "year": year, "quarter": quarter})

calls.sort(key=lambda x: x["date"])
print(f"Loaded {len(calls)} call dates:")
for c in calls:
    print(f"  {c['label']}  {c['date'].date()}")

# ── 2. Download price data ───────────────────────────────────────────────────
# Extend to 2025-03-01 to cover 2024Q4 call (2025-01-29) + 5 trading days
print("\nDownloading TSLA and ^GSPC prices...")
prices = yf.download(["TSLA", "^GSPC"], start="2020-12-01", end="2025-03-01",
                     auto_adjust=True, progress=False)["Close"]
prices.columns = ["GSPC", "TSLA"]
prices = prices.dropna()

# Daily log returns
rets = prices.pct_change()

print(f"Price data: {prices.index[0].date()} to {prices.index[-1].date()}, {len(prices)} trading days")

# ── 3. Compute per-call returns ──────────────────────────────────────────────
trading_days = prices.index

def nth_trading_day(ref_date, n):
    """Return the n-th trading day relative to ref_date (0 = same day or next)."""
    pos = trading_days.searchsorted(ref_date)
    if pos >= len(trading_days):
        return None
    target = pos + n
    if target < 0 or target >= len(trading_days):
        return None
    return trading_days[target]

records = []
for call in calls:
    d0 = call["date"]

    # Find the actual trading day on or after the call date
    pos0 = trading_days.searchsorted(d0)
    if pos0 >= len(trading_days):
        print(f"  WARNING: {call['label']} date {d0.date()} outside price data — skipping")
        continue

    # If market was closed on call date, use next trading day as day 0
    actual_d0 = trading_days[pos0]
    if actual_d0 != d0:
        print(f"  NOTE: {call['label']} call date {d0.date()} → using {actual_d0.date()} as day 0")

    # Day 0 return
    r0_tsla = rets["TSLA"].iloc[pos0] if pos0 < len(rets) else None
    r0_gspc = rets["GSPC"].iloc[pos0] if pos0 < len(rets) else None

    # Days +1 to +5 cumulative return
    cum_tsla = 1.0
    cum_gspc = 1.0
    available_days = 0
    for k in range(1, 6):
        pos_k = pos0 + k
        if pos_k >= len(rets):
            break
        r_tsla = rets["TSLA"].iloc[pos_k]
        r_gspc = rets["GSPC"].iloc[pos_k]
        if pd.isna(r_tsla) or pd.isna(r_gspc):
            break
        cum_tsla *= (1 + r_tsla)
        cum_gspc *= (1 + r_gspc)
        available_days += 1

    cum_ret_tsla = (cum_tsla - 1) * 100 if available_days > 0 else None
    cum_ret_gspc = (cum_gspc - 1) * 100 if available_days > 0 else None
    abnormal = (cum_ret_tsla - cum_ret_gspc) if (cum_ret_tsla is not None and cum_ret_gspc is not None) else None
    direction = "positive" if (abnormal is not None and abnormal >= 0) else "negative"

    records.append({
        "label":              call["label"],
        "call_date":          d0.date(),
        "trading_day_0":      actual_d0.date(),
        "day0_tsla_pct":      round(r0_tsla * 100, 4) if r0_tsla is not None else None,
        "day0_gspc_pct":      round(r0_gspc * 100, 4) if r0_gspc is not None else None,
        "cum_1to5_tsla_pct":  round(cum_ret_tsla, 4) if cum_ret_tsla is not None else None,
        "cum_1to5_gspc_pct":  round(cum_ret_gspc, 4) if cum_ret_gspc is not None else None,
        "abnormal_ret_pct":   round(abnormal, 4) if abnormal is not None else None,
        "direction":          direction,
        "days_available":     available_days,
    })

df = pd.DataFrame(records)
csv_path = OUT_DIR / "TSLA_returns_by_call.csv"
df.to_csv(csv_path, index=False)
print(f"\nSaved {csv_path.name}  ({len(df)} rows)")
print(df[["label", "day0_tsla_pct", "cum_1to5_tsla_pct", "cum_1to5_gspc_pct",
          "abnormal_ret_pct", "direction"]].to_string(index=False))

# ── 4. Plot TSLA price timeline ──────────────────────────────────────────────
# Restrict plot to 2021-01-01 to 2024-12-31
plot_prices = prices["TSLA"].loc["2021-01-01":"2024-12-31"]

fig, ax = plt.subplots(figsize=(16, 6))
ax.plot(plot_prices.index, plot_prices.values, color="#1f77b4", linewidth=1.2, label="TSLA Close")

# Add call-date vertical lines, colour by direction
for rec in records:
    call_dt = pd.Timestamp(rec["trading_day_0"])
    if not (pd.Timestamp("2021-01-01") <= call_dt <= pd.Timestamp("2024-12-31")):
        continue
    color = "#2ca02c" if rec["direction"] == "positive" else "#d62728"
    ax.axvline(x=call_dt, color=color, linewidth=1.1, linestyle="--", alpha=0.85)

    # Label: offset alternately up/down to reduce overlap
    y_min, y_max = ax.get_ylim()
    if y_max == y_min:
        y_min, y_max = plot_prices.min(), plot_prices.max()
    price_at_call = plot_prices.asof(call_dt) if call_dt in plot_prices.index else plot_prices.iloc[-1]
    y_pos = price_at_call + (plot_prices.max() - plot_prices.min()) * 0.03
    ax.text(call_dt, y_pos, rec["label"], rotation=90, fontsize=6,
            ha="center", va="bottom", color=color, clip_on=True)

# Legend patches
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor="#2ca02c", label="Positive 5-day abnormal return"),
    Patch(facecolor="#d62728", label="Negative 5-day abnormal return"),
]
ax.legend(handles=legend_elements, loc="upper right", fontsize=9)

ax.set_title("Tesla (TSLA) Stock Price 2021–2024 with Earnings Call Dates", fontsize=13)
ax.set_xlabel("")
ax.set_ylabel("Price (USD)", fontsize=10)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.xticks(rotation=45, ha="right", fontsize=8)
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%.0f"))
ax.grid(axis="y", linestyle=":", alpha=0.5)
plt.tight_layout()

img_path = OUT_DIR / "TSLA_price_timeline.png"
plt.savefig(img_path, dpi=150)
plt.close()
print(f"\nSaved {img_path.name}")

# ── 5. Upload to Google Drive ────────────────────────────────────────────────
import subprocess

def rclone_upload(local_path: Path):
    cmd = [
        "rclone", "copy",
        str(local_path),
        f"gdrive:{local_path.name}",
        f"--drive-root-folder-id={DRIVE_FOLDER}",
        "-v",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"  Uploaded {local_path.name} to Google Drive")
    else:
        print(f"  ERROR uploading {local_path.name}: {r.stderr}")

print("\nUploading to Google Drive...")
rclone_upload(csv_path)
rclone_upload(img_path)

print("\nDone.")
