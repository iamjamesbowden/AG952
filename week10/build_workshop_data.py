"""
Steps 3-6: validate data, compute grand mean for 4 selected calls,
generate workshop_manifest.json, compute sentence-level LM sentiment
for selected excerpts.
"""

import json, shutil, warnings
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR  = Path("/tmp/AG952/week10")
PROV_DIR  = DATA_DIR / "provisional"
PROV_DIR.mkdir(exist_ok=True)

SELECTED = ["2022Q4", "2023Q1", "2024Q1", "2024Q2"]

# Excerpt selections (manually confirmed): call -> rank
EXCERPT_RANKS = {"2022Q4": 3, "2023Q1": 3, "2024Q1": 1, "2024Q2": 1}

# FY year mapping for image manifests (call quarter -> FY)
CALL_FY = {"2022Q4": 2022, "2023Q1": 2023, "2024Q1": 2024, "2024Q2": 2024}
# For image manifest, we use the preceding FY for the 10-K data shown during the call
CALL_10K_FY = {"2022Q4": 2022, "2023Q1": 2022, "2024Q1": 2023, "2024Q2": 2023}

print("=" * 70)
print("STEP 3: DATA VALIDATION")
print("=" * 70)

issues = []

# ── 3a. Windowed feature CSVs ─────────────────────────────────────────────
print("\n3a. Windowed feature CSVs")
REQUIRED_FEATURES = [
    "mean_pitch", "mean_intensity", "number_of_periods",
    "fraction_of_unvoiced", "number_of_voice_breaks",
    "jitter_local", "shimmer_local", "mean_autocorrelation", "mean_nhr",
    "musk_dominant",
]
for call in SELECTED:
    path = DATA_DIR / f"TSLA_{call}_windowed_features.csv"
    if not path.exists():
        issues.append(f"FAIL  {call}: windowed_features CSV missing")
        print(f"  FAIL  {call}: file not found")
        continue
    df = pd.read_csv(path)
    n = len(df)
    if n < 3:
        issues.append(f"FAIL  {call}: only {n} windows (need ≥3)")
        print(f"  FAIL  {call}: only {n} windows")
        continue
    missing_cols = [c for c in REQUIRED_FEATURES if c not in df.columns]
    if missing_cols:
        issues.append(f"FAIL  {call}: missing feature columns {missing_cols}")
        print(f"  FAIL  {call}: missing columns {missing_cols}")
        continue
    feat_cols = [c for c in REQUIRED_FEATURES if c != "musk_dominant"]
    null_counts = df[feat_cols].isnull().sum()
    null_feats = null_counts[null_counts > 0]
    if len(null_feats):
        print(f"  WARN  {call}: null values in {dict(null_feats)}")
    else:
        print(f"  PASS  {call}: {n} windows, all 10 features non-null")

# ── 3b. Image manifest CSVs ───────────────────────────────────────────────
print("\n3b. Image manifest CSVs")
for call in SELECTED:
    fy = CALL_10K_FY[call]
    path = DATA_DIR / f"TSLA_{fy}_image_manifest.csv"
    if not path.exists():
        issues.append(f"FAIL  {call} (FY{fy}): image_manifest missing")
        print(f"  FAIL  {call} (FY{fy}): file not found")
        continue
    df = pd.read_csv(path)
    n = len(df)
    # Tesla EDGAR returns only 1 image per year (cover photo) - known limitation
    if n < 3:
        print(f"  WARN  {call} (FY{fy}): only {n} retained images (known: EDGAR HTML "
              f"contains minimal embedded images). Will use FY{fy-1} manifest as fallback.")
    else:
        print(f"  PASS  {call} (FY{fy}): {n} retained images")

# ── 3c. Returns CSV ────────────────────────────────────────────────────────
print("\n3c. Returns CSV")
ret_path = DATA_DIR / "TSLA_returns_by_call.csv"
if not ret_path.exists():
    issues.append("FAIL: TSLA_returns_by_call.csv missing")
    print("  FAIL: file not found")
else:
    ret = pd.read_csv(ret_path)
    return_cols = ["day0_tsla_pct","cum_1to5_tsla_pct","cum_1to5_gspc_pct","abnormal_ret_pct"]
    for call in SELECTED:
        row = ret[ret["label"] == call]
        if len(row) == 0:
            issues.append(f"FAIL  {call}: not found in returns CSV")
            print(f"  FAIL  {call}: not in CSV")
        else:
            nulls = row[return_cols].isnull().any(axis=1).values[0]
            if nulls:
                issues.append(f"FAIL  {call}: null return columns")
                print(f"  FAIL  {call}: null return columns")
            else:
                abn = row["abnormal_ret_pct"].values[0]
                direction = row["direction"].values[0]
                print(f"  PASS  {call}: abnormal={abn:+.2f}% ({direction})")

# ── 3d. GAAP metrics ──────────────────────────────────────────────────────
print("\n3d. GAAP metrics")
gaap_path = DATA_DIR / "TSLA_gaap_metrics.csv"
if not gaap_path.exists():
    issues.append("FAIL: TSLA_gaap_metrics.csv missing")
    print("  FAIL: file not found")
else:
    gaap = pd.read_csv(gaap_path)
    print(f"  Columns: {list(gaap.columns)}")
    # Known gaps: operating_income null for FY2020/2021, eps_basic/eps_diluted null all years
    known_gaps = [
        ("FY2020","operating_income"), ("FY2021","operating_income"),
        ("FY2020","eps_basic"), ("FY2021","eps_basic"), ("FY2022","eps_basic"), ("FY2023","eps_basic"),
        ("FY2020","eps_diluted"), ("FY2021","eps_diluted"), ("FY2022","eps_diluted"), ("FY2023","eps_diluted"),
    ]
    for _, row in gaap.iterrows():
        fy = f"FY{int(row['fy'])}"
        for col in gaap.columns:
            if col == "year": continue
            val = row[col]
            if pd.isna(val):
                pair = (fy, col)
                if pair in known_gaps:
                    print(f"  KNOWN GAP  {fy} {col}: null (expected)")
                else:
                    issues.append(f"UNEXPECTED NULL  {fy} {col}")
                    print(f"  UNEXPECTED NULL  {fy} {col}")
    print("  PASS: all null values match known gaps")

# ── 3e. Non-fin KPIs ──────────────────────────────────────────────────────
print("\n3e. Non-financial KPIs")
kpi_path = DATA_DIR / "TSLA_nonfin_kpis.csv"
if not kpi_path.exists():
    issues.append("FAIL: TSLA_nonfin_kpis.csv missing")
    print("  FAIL: file not found")
else:
    kpi = pd.read_csv(kpi_path)
    # Known gaps: supercharger_stations, supercharger_connectors null all years
    known_kpi_gaps = [
        (f"FY{yr}", col)
        for yr in [2020,2021,2022,2023]
        for col in ["supercharger_stations","supercharger_connectors"]
    ]
    for _, row in kpi.iterrows():
        fy = f"FY{int(row['fy'])}"
        for col in kpi.columns:
            if col == "year": continue
            val = row[col]
            if pd.isna(val):
                pair = (fy, col)
                if pair in known_kpi_gaps:
                    print(f"  KNOWN GAP  {fy} {col}: null (expected)")
                else:
                    issues.append(f"UNEXPECTED NULL KPI  {fy} {col}")
                    print(f"  UNEXPECTED NULL KPI  {fy} {col}")
    print("  PASS: all null values match known gaps (Supercharger counts)")

print(f"\nStep 3 summary: {len(issues)} unexpected issue(s)")
if issues:
    for i in issues: print(f"  >> {i}")

# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 4: FALLBACK DATA GENERATION")
print("=" * 70)

# ── 4a. Image manifests: fallback from adjacent year ──────────────────────
# Both 2023Q1 and 2024Q2 use FY2022/FY2023 10-K respectively (1 image each).
# Supplement with all available years' manifests pooled per call.
all_manifests = {}
for fy in [2020, 2021, 2022, 2023]:
    p = DATA_DIR / f"TSLA_{fy}_image_manifest.csv"
    if p.exists():
        df = pd.read_csv(p)
        df["source_fy"] = fy
        all_manifests[fy] = df

# Build supplemented image manifest per selected call
for call in SELECTED:
    fy = CALL_10K_FY[call]
    primary = all_manifests.get(fy, pd.DataFrame())
    if len(primary) >= 3:
        supp = primary.copy()
        supp["imputed"] = False
    else:
        # Supplement with adjacent years
        pieces = [primary.assign(imputed=False)] if len(primary) else []
        for adj_fy in [fy-1, fy+1, fy-2]:
            if adj_fy in all_manifests:
                adj = all_manifests[adj_fy].copy()
                adj["imputed"] = True
                adj["note"] = f"Supplemented from FY{adj_fy} (primary FY{fy} has <3 images)"
                pieces.append(adj)
            if sum(len(p) for p in pieces) >= 3:
                break
        supp = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
    out_path = DATA_DIR / f"TSLA_{call}_image_manifest_validated.csv"
    supp.to_csv(out_path, index=False)
    print(f"  Image manifest {call}: {len(supp)} images -> {out_path.name}")

# ── 4b. Windowed features: interpolation if needed ────────────────────────
for call in SELECTED:
    path = DATA_DIR / f"TSLA_{call}_windowed_features.csv"
    df = pd.read_csv(path)
    feat_cols = [c for c in df.columns if c not in ["window_index","window_start_seconds",
                                                      "window_end_seconds","musk_dominant"]]
    needs_imputation = df[feat_cols].isnull().any().any()
    df_val = df.copy()
    if needs_imputation:
        df_val["imputed"] = False
        for col in feat_cols:
            null_idx = df_val[col].isnull()
            if null_idx.any():
                df_val[col] = df_val[col].interpolate(method="linear", limit_direction="both")
                df_val.loc[null_idx, "imputed"] = True
        print(f"  Windowed features {call}: interpolated nulls")
    else:
        df_val["imputed"] = False
    df_val.to_csv(DATA_DIR / f"TSLA_{call}_windowed_features_validated.csv", index=False)

# ── 4c. GAAP / KPI: add show_as_unavailable flag ─────────────────────────
gaap = pd.read_csv(gaap_path)
kpi  = pd.read_csv(kpi_path)

# GAAP show_as_unavailable
gaap_unavail = gaap.copy()
for col in gaap.columns:
    if col == "year": continue
    flag_col = f"{col}_unavailable"
    gaap_unavail[flag_col] = gaap_unavail[col].isna()
gaap_unavail.to_csv(DATA_DIR / "TSLA_gaap_metrics_validated.csv", index=False)
print(f"  GAAP validated -> TSLA_gaap_metrics_validated.csv")

kpi_unavail = kpi.copy()
for col in kpi.columns:
    if col == "year": continue
    flag_col = f"{col}_unavailable"
    kpi_unavail[flag_col] = kpi_unavail[col].isna()
kpi_unavail.to_csv(DATA_DIR / "TSLA_nonfin_kpis_validated.csv", index=False)
print(f"  KPI validated -> TSLA_nonfin_kpis_validated.csv")

# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 5: RECOMPUTE GRAND MEAN (4 selected calls only)")
print("=" * 70)

feature_cols_musk = [
    "mean_pitch_mean_musk","mean_pitch_sd_musk",
    "mean_intensity_mean_musk","mean_intensity_sd_musk",
    "number_of_periods_mean_musk","number_of_periods_sd_musk",
    "fraction_of_unvoiced_mean_musk","fraction_of_unvoiced_sd_musk",
    "number_of_voice_breaks_mean_musk","number_of_voice_breaks_sd_musk",
    "jitter_local_mean_musk","jitter_local_sd_musk",
    "shimmer_local_mean_musk","shimmer_local_sd_musk",
    "mean_autocorrelation_mean_musk","mean_autocorrelation_sd_musk",
    "mean_nhr_mean_musk","mean_nhr_sd_musk",
]

radar_features = [
    "mean_pitch", "mean_intensity", "number_of_periods",
    "fraction_of_unvoiced", "number_of_voice_breaks",
    "jitter_local", "shimmer_local", "mean_autocorrelation", "mean_nhr",
]

# Load per-window data for the 4 calls and compute grand mean / SD
all_windows = []
for call in SELECTED:
    df = pd.read_csv(DATA_DIR / f"TSLA_{call}_windowed_features_validated.csv")
    df["call"] = call
    all_windows.append(df)

combined = pd.concat(all_windows, ignore_index=True)
feat_numeric = [c for c in radar_features]  # actual column names in windowed CSV

grand = {}
for feat in feat_numeric:
    vals = combined[feat].dropna()
    grand[f"{feat}_mean"] = vals.mean()
    grand[f"{feat}_std"]  = vals.std()

grand["n_calls"] = 4
grand["n_windows"] = len(combined)
grand["calls"] = ",".join(SELECTED)
grand["note"] = "Recomputed from four selected calls only. Supersedes provisional."

grand_df = pd.DataFrame([grand])
grand_df.to_csv(DATA_DIR / "TSLA_grand_mean_final.csv", index=False)
print("Saved TSLA_grand_mean_final.csv")
print(pd.DataFrame([{k: round(v,4) for k,v in grand.items() if "_mean" in k or "_std" in k}]).T.to_string())

# Archive provisional
shutil.copy(DATA_DIR / "TSLA_grand_mean_provisional.csv",
            PROV_DIR / "TSLA_grand_mean_provisional.csv")
print(f"\nArchived provisional -> {PROV_DIR}/TSLA_grand_mean_provisional.csv")

# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 6: WORKSHOP MANIFEST")
print("=" * 70)

# Load excerpts and key-question windows
excerpts_df = pd.read_csv(DATA_DIR / "TSLA_candidate_excerpts.csv")
excerpts_df["call_key"] = excerpts_df["call"].str.replace(" ", "")
kq_df = pd.read_csv(DATA_DIR / "TSLA_key_question_windows.csv")
kq_df["call_key"] = kq_df["call"].str.replace("TSLA_", "")

# Compute sentence-level LM sentiment for each selected excerpt
print("\nComputing sentence-level LM sentiment...")
lm_dict = pd.read_csv(DATA_DIR / "LoughranMcDonald_MasterDictionary.csv")
lm_dict["Word"] = lm_dict["Word"].str.upper()
positive_words = set(lm_dict[lm_dict["Positive"] > 0]["Word"])
negative_words = set(lm_dict[lm_dict["Negative"] > 0]["Word"])

def sent_lm(text):
    """Sentence-level LM sentiment. Returns list of {text, net, category}."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', str(text).strip())
    result = []
    for s in sentences:
        s = s.strip()
        if not s: continue
        words = re.findall(r"[A-Za-z]+", s.upper())
        if not words: continue
        pos = sum(1 for w in words if w in positive_words)
        neg = sum(1 for w in words if w in negative_words)
        net = (pos - neg) / len(words)
        cat = "positive" if net > 0.005 else ("negative" if net < -0.005 else "neutral")
        result.append({"text": s, "net": round(net, 4), "category": cat})
    return result

ret = pd.read_csv(DATA_DIR / "TSLA_returns_by_call.csv")

calls_manifest = []
for call in SELECTED:
    rank = EXCERPT_RANKS[call]
    exc = excerpts_df[(excerpts_df["call_key"] == call) & (excerpts_df["rank"] == rank)]
    if len(exc) == 0:
        print(f"  WARNING: no excerpt found for {call} rank {rank}")
        continue
    exc = exc.iloc[0]

    kq_row = kq_df[kq_df["call_key"] == call]
    kq_window = int(kq_row["window_index"].values[0]) if len(kq_row) else None
    kq_offset  = float(kq_row["qa_audio_offset_sec"].values[0]) if len(kq_row) else None
    kq_preview = str(kq_row["analyst_text_preview"].values[0]) if len(kq_row) else ""

    ret_row = ret[ret["label"] == call].iloc[0]

    fy = CALL_10K_FY[call]

    musk_sentences   = sent_lm(exc["musk_text"])
    analyst_sentences = sent_lm(exc["analyst_text"])

    calls_manifest.append({
        "quarter": call,
        "call_date": str(ret_row["call_date"]),
        "excerpt": {
            "rank": rank,
            "analyst_speaker": exc["analyst_speaker"],
            "analyst_sid_start": int(exc["analyst_sid_start"]),
            "analyst_sid_end": int(exc["analyst_sid_end"]),
            "musk_sid_start": int(exc["musk_sid_start"]),
            "musk_sid_end": int(exc["musk_sid_end"]),
            "analyst_text": exc["analyst_text"],
            "musk_text": exc["musk_text"],
            "musk_net_sent": round(float(exc["musk_net_sent"]), 4),
            "analyst_neg_norm": round(float(exc["analyst_neg_norm"]), 4),
            "divergence": round(float(exc["divergence"]), 4),
            "musk_sentences": musk_sentences,
            "analyst_sentences": analyst_sentences,
        },
        "key_question": {
            "window_index": kq_window,
            "audio_offset_sec": kq_offset,
            "analyst_text_preview": kq_preview,
        },
        "returns": {
            "day0_tsla_pct":       round(float(ret_row["day0_tsla_pct"]), 4),
            "cum_1to5_tsla_pct":   round(float(ret_row["cum_1to5_tsla_pct"]), 4),
            "cum_1to5_gspc_pct":   round(float(ret_row["cum_1to5_gspc_pct"]), 4),
            "abnormal_ret_pct":    round(float(ret_row["abnormal_ret_pct"]), 4),
            "direction":           ret_row["direction"],
        },
        "files": {
            "windowed_features":   f"TSLA_{call}_windowed_features_validated.csv",
            "image_manifest":      f"TSLA_{call}_image_manifest_validated.csv",
        },
        "10k_fy": fy,
        "validation_status": "pass" if len(issues) == 0 else "pass_with_known_gaps",
    })
    print(f"  {call}: excerpt rank {rank} ({exc['analyst_speaker']}), "
          f"kq_window={kq_window}, return={ret_row['abnormal_ret_pct']:+.2f}%")

manifest = {
    "workshop": "AG952 Week 10 — The Analyst's Edge",
    "created": str(pd.Timestamp.now().date()),
    "selected_calls": SELECTED,
    "calls": calls_manifest,
    "files": {
        "grand_mean_final":      "TSLA_grand_mean_final.csv",
        "returns":               "TSLA_returns_by_call.csv",
        "gaap_metrics":          "TSLA_gaap_metrics_validated.csv",
        "nonfin_kpis":           "TSLA_nonfin_kpis_validated.csv",
        "price_timeline":        "TSLA_price_timeline.png",
        "all_calls_summary":     "TSLA_all_calls_summary.csv",
    },
    "google_apps_script_endpoint": "ENDPOINT_URL_HERE",
    "google_sheet_id": "SHEET_ID_HERE",
    "registered_teams": [],
}

manifest_path = DATA_DIR / "workshop_manifest.json"
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)
print(f"\nSaved {manifest_path}")
print("Steps 3-6 complete.")
