"""Build AG952_Week10_Workshop.ipynb as raw JSON — avoids all triple-quote nesting."""
import json
from pathlib import Path

# ─── helpers ──────────────────────────────────────────────────────────────────
def code_cell(lines, hidden=False, title=""):
    """lines: list of code strings (newline already included at end of each)."""
    if hidden:
        lines = [f"# @title {title} {{display-mode: \"form\"}}\n"] + lines
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"cellView": "form"} if hidden else {},
        "outputs": [],
        "source": lines,
    }

def md_cell(lines):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": lines,
    }

def L(*args):
    """Join args as a single source line with newline."""
    return "".join(args) + "\n"

# ─── notebook metadata ─────────────────────────────────────────────────────────
nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
        "colab": {"provenance": []},
    },
    "cells": [],
}

cells = nb["cells"]

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 0 — Setup (hidden)
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(code_cell([
    L("import subprocess, sys"),
    L("subprocess.run([sys.executable, '-m', 'pip', 'install',"),
    L("                'ipywidgets', 'plotly', '--quiet'], capture_output=True)"),
    L("from google.colab import drive"),
    L("drive.mount('/content/drive', force_remount=False)"),
    L("DRIVE_ROOT = '/content/drive/MyDrive/workshop_data'"),
    L("import warnings; warnings.filterwarnings('ignore')"),
    L("print('Drive mounted.'  )"),
], hidden=True, title="\u2699 Setup \u2014 run first"))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 1 — Load data (hidden)
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(code_cell([
    L("import json, re, os, urllib.request"),
    L("import numpy as np"),
    L("import pandas as pd"),
    L("import matplotlib; matplotlib.use('Agg')"),
    L("import matplotlib.pyplot as plt"),
    L("import plotly.graph_objects as go"),
    L("import ipywidgets as widgets"),
    L("from IPython.display import display, HTML, Image, clear_output"),
    L("from pathlib import Path"),
    L(""),
    L("with open(f'{DRIVE_ROOT}/workshop_manifest.json') as _f:"),
    L("    MANIFEST = json.load(_f)"),
    L(""),
    L("CALLS    = MANIFEST['calls']"),
    L("ENDPOINT = MANIFEST['google_apps_script_endpoint']"),
    L("QUARTERS = [c['quarter'] for c in CALLS]"),
    L(""),
    L("def dpath(fname): return f'{DRIVE_ROOT}/{fname}'"),
    L(""),
    L("RETURNS    = pd.read_csv(dpath(MANIFEST['files']['returns']))"),
    L("GAAP       = pd.read_csv(dpath(MANIFEST['files']['gaap_metrics']))"),
    L("KPI        = pd.read_csv(dpath(MANIFEST['files']['nonfin_kpis']))"),
    L("GRAND_MEAN = pd.read_csv(dpath(MANIFEST['files']['grand_mean_final'])).iloc[0]"),
    L("SUMMARY    = pd.read_csv(dpath(MANIFEST['files']['all_calls_summary']))"),
    L(""),
    L("FEATURES = {}"),
    L("IMG_MFST = {}"),
    L("for _c in CALLS:"),
    L("    _q = _c['quarter']"),
    L("    FEATURES[_q] = pd.read_csv(dpath(_c['files']['windowed_features']))"),
    L("    IMG_MFST[_q] = pd.read_csv(dpath(_c['files']['image_manifest']))"),
    L(""),
    L("CLR = {"),
    L("    'lm_positive':  '#22c55e',"),
    L("    'lm_negative':  '#ef4444',"),
    L("    'lm_neutral':   '#9ca3af',"),
    L("    'fou_above':    '#f59e0b',"),
    L("    'fou_below':    '#3b82f6',"),
    L("    'ret_positive': '#22c55e',"),
    L("    'ret_negative': '#ef4444',"),
    L("    'analyst_text': '#fbbf24',"),
    L("    'musk_text':    '#60a5fa',"),
    L("}"),
    L(""),
    L("STATE = {"),
    L("    'team_name': '', 'registered': False,"),
    L("    'r1_submitted': False, 'r2_submitted': False, 'r3_submitted': False,"),
    L("    'r2_chip_shift_used': False, 'r3_chip_shift_used': False,"),
    L("    'chips': {q: 3 for q in QUARTERS},"),
    L("}"),
    L("print('Data loaded. Calls:', QUARTERS)"),
], hidden=True, title="\U0001f4e6 Load data"))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 2 — CSS + utilities (hidden)
# ═══════════════════════════════════════════════════════════════════════════════
css = (
    "<style>\n"
    "  .ag-card{background:#1e293b;border:1px solid #334155;border-radius:8px;"
    "padding:16px;margin:8px;font-family:'Georgia',serif;color:#e2e8f0;}\n"
    "  .ag-card h4{color:#818cf8;margin:0 0 8px 0;font-size:1.1em;}\n"
    "  .ag-excerpt-box{background:#0f172a;border-left:3px solid #334155;"
    "padding:10px 14px;border-radius:4px;font-size:0.88em;line-height:1.6;margin:8px 0;}\n"
    "  .ag-analyst{color:#fbbf24;}\n"
    "  .ag-musk{color:#60a5fa;}\n"
    "  .ag-label{color:#94a3b8;font-size:0.8em;text-transform:uppercase;"
    "letter-spacing:0.05em;margin-bottom:2px;}\n"
    "  .ag-gauge-pos{color:#22c55e;font-size:1.4em;font-weight:bold;}\n"
    "  .ag-gauge-neg{color:#ef4444;font-size:1.4em;font-weight:bold;}\n"
    "  .ag-gauge-neu{color:#9ca3af;font-size:1.4em;font-weight:bold;}\n"
    "  .ag-section-hdr{background:linear-gradient(90deg,#1e293b,#0f172a);"
    "border-left:4px solid #818cf8;padding:10px 16px;margin:20px 0 10px 0;"
    "font-family:'Georgia',serif;color:#e2e8f0;font-size:1.1em;}\n"
    "  .ag-status-box{background:#1e293b;border:1px solid #334155;border-radius:6px;"
    "padding:12px;font-family:monospace;font-size:0.85em;color:#94a3b8;}\n"
    "  .ag-table{border-collapse:collapse;width:100%;}\n"
    "  .ag-table th{background:#334155;color:#e2e8f0;padding:6px 10px;"
    "text-align:left;font-size:0.85em;}\n"
    "  .ag-table td{padding:5px 10px;font-size:0.85em;border-bottom:1px solid #1e293b;}\n"
    "  .ag-table tr:nth-child(even){background:#1e293b;}\n"
    "  .ag-table tr:nth-child(odd){background:#0f172a;}\n"
    "  .ag-arrow-up{color:#22c55e;font-weight:bold;}\n"
    "  .ag-arrow-down{color:#ef4444;font-weight:bold;}\n"
    "  .ag-arrow-flat{color:#9ca3af;}\n"
    "  .ag-na{color:#475569;font-style:italic;}\n"
    "  .ag-word-counter{font-size:0.78em;color:#94a3b8;text-align:right;margin-top:2px;}\n"
    "</style>\n"
)
cells.append(code_cell([
    L("display(HTML(", repr(css), "))"),
    L(""),
    L("def post_to_script(payload):"),
    L("    if ENDPOINT == 'ENDPOINT_URL_HERE':"),
    L("        print('Apps Script endpoint not configured (offline mode).')"),
    L("        return {'success': True, 'message': 'offline'}"),
    L("    import json as _j"),
    L("    req = urllib.request.Request(ENDPOINT,"),
    L("        data=_j.dumps(payload).encode(),"),
    L("        headers={'Content-Type': 'application/json'}, method='POST')"),
    L("    with urllib.request.urlopen(req, timeout=15) as r:"),
    L("        return _j.loads(r.read())"),
    L(""),
    L("def get_status(round_number):"),
    L("    try: return post_to_script({'action':'get_status','round':round_number})"),
    L("    except: return {'submitted_teams':[],'total':'?'}"),
    L(""),
    L("def render_sentiment_bars(ax, sentences, title=''):"),
    L("    nets  = [s['net'] for s in sentences]"),
    L("    cats  = [s['category'] for s in sentences]"),
    L("    colors = [CLR['lm_positive'] if c=='positive' else"),
    L("              CLR['lm_negative'] if c=='negative' else CLR['lm_neutral']"),
    L("              for c in cats]"),
    L("    ax.bar(range(len(sentences)), nets, color=colors, width=0.7)"),
    L("    ax.axhline(0, color='#475569', linewidth=0.8)"),
    L("    ax.set_xticks(range(len(sentences)))"),
    L("    ax.set_xticklabels([f'S{i+1}' for i in range(len(sentences))],"),
    L("                       fontsize=7, color='#94a3b8')"),
    L("    ax.set_ylabel('LM net', fontsize=7, color='#94a3b8')"),
    L("    ax.tick_params(axis='y', labelsize=7, colors='#94a3b8')"),
    L("    ax.set_facecolor('#0f172a')"),
    L("    for sp in ['top','right']: ax.spines[sp].set_visible(False)"),
    L("    for sp in ['bottom','left']: ax.spines[sp].set_color('#334155')"),
    L("    if title: ax.set_title(title, fontsize=8, color='#818cf8', pad=4)"),
    L(""),
    L("FOU_MEAN = float(GRAND_MEAN['fraction_of_unvoiced_mean'])"),
    L(""),
    L("RADAR_FEATS  = ['mean_pitch','mean_intensity','number_of_periods',"),
    L("                'fraction_of_unvoiced','number_of_voice_breaks',"),
    L("                'jitter_local','shimmer_local','mean_autocorrelation','mean_nhr']"),
    L("RADAR_LABELS = ['Pitch','Intensity','Voiced rate','Silence','Hesitation',"),
    L("                'Freq stability','Amp stability','Vocal clarity','Breathiness']"),
    L(""),
    L("def z_score(val, feat):"),
    L("    mu  = GRAND_MEAN.get(f'{feat}_mean', np.nan)"),
    L("    sig = GRAND_MEAN.get(f'{feat}_std',  np.nan)"),
    L("    if not sig or np.isnan(sig): return 0.0"),
    L("    return (val - mu) / sig"),
    L(""),
    L("def make_silence_map(c):"),
    L("    q = c['quarter']"),
    L("    df = FEATURES[q].copy()"),
    L("    kq = c['key_question']['window_index']"),
    L("    kq_text = (c['key_question']['analyst_text_preview'] or '')[:80]"),
    L("    colors = [CLR['fou_above'] if v > FOU_MEAN else CLR['fou_below']"),
    L("              for v in df['fraction_of_unvoiced']]"),
    L("    fig = go.Figure()"),
    L("    fig.add_trace(go.Bar(x=df['window_index'], y=df['fraction_of_unvoiced'],"),
    L("        marker_color=colors,"),
    L("        hovertemplate='<b>Window %{x}</b><br>FoU: %{y:.3f}<extra></extra>'))"),
    L("    fig.add_hline(y=FOU_MEAN, line_dash='dot', line_color='#94a3b8',"),
    L("        annotation_text=f'Mean ({FOU_MEAN:.3f})',"),
    L("        annotation_font_color='#94a3b8', annotation_font_size=10)"),
    L("    if kq is not None and kq < len(df):"),
    L("        fig.add_vline(x=kq, line_dash='dash', line_color='#818cf8',"),
    L("            annotation_text='Key Q', annotation_font_color='#818cf8',"),
    L("            annotation_font_size=10)"),
    L("    fig.update_layout("),
    L("        title=dict(text=f'{q} \u2014 Silence patterns across the Q&A',"),
    L("                   font=dict(color='#e2e8f0', size=13)),"),
    L("        xaxis=dict(title='5-min window', color='#94a3b8', gridcolor='#1e293b'),"),
    L("        yaxis=dict(title='Fraction of unvoiced (0\u20131)', range=[0,1],"),
    L("                   color='#94a3b8', gridcolor='#1e293b'),"),
    L("        plot_bgcolor='#0f172a', paper_bgcolor='#1e293b',"),
    L("        font=dict(color='#e2e8f0'), height=260,"),
    L("        margin=dict(l=50,r=20,t=50,b=40), showlegend=False)"),
    L("    return fig"),
    L(""),
    L("def make_radar(c):"),
    L("    q = c['quarter']"),
    L("    row = SUMMARY[SUMMARY['call'] == f'TSLA_{q}']"),
    L("    if len(row) == 0: return go.Figure()"),
    L("    row = row.iloc[0]"),
    L("    MAX_Z = 3.0"),
    L("    def norm(z): return max(0, min(1, (z + MAX_Z) / (2 * MAX_Z)))"),
    L("    r_call = []"),
    L("    flags  = []"),
    L("    for feat in RADAR_FEATS:"),
    L("        val = row.get(f'{feat}_mean_musk', np.nan)"),
    L("        if pd.isna(val): val = 0.0"),
    L("        z = z_score(val, feat)"),
    L("        r_call.append(norm(z))"),
    L("        flags.append(abs(z) > 1.0)"),
    L("    r_grand = [0.5] * len(RADAR_FEATS)"),
    L("    labels  = RADAR_LABELS"),
    L("    fig = go.Figure()"),
    L("    fig.add_trace(go.Scatterpolar(r=r_call+[r_call[0]], theta=labels+[labels[0]],"),
    L("        fill='toself', fillcolor='rgba(96,165,250,0.15)',"),
    L("        line=dict(color='#60a5fa', width=2), name=q))"),
    L("    fig.add_trace(go.Scatterpolar(r=r_grand+[r_grand[0]], theta=labels+[labels[0]],"),
    L("        fill='none', line=dict(color='#475569', width=1, dash='dot'),"),
    L("        name='Cross-call average'))"),
    L("    for i,(feat,flag) in enumerate(zip(RADAR_FEATS, flags)):"),
    L("        if flag:"),
    L("            fig.add_trace(go.Scatterpolar(r=[r_call[i]], theta=[labels[i]],"),
    L("                mode='markers', marker=dict(color='#f59e0b', size=10),"),
    L("                showlegend=False))"),
    L("    fig.update_layout("),
    L("        polar=dict(bgcolor='#0f172a',"),
    L("            radialaxis=dict(visible=True, range=[0,1], color='#475569',"),
    L("                            gridcolor='#334155', tickfont_size=7),"),
    L("            angularaxis=dict(color='#94a3b8', gridcolor='#334155')),"),
    L("        showlegend=True,"),
    L("        legend=dict(font=dict(color='#94a3b8', size=9), bgcolor='rgba(0,0,0,0)'),"),
    L("        paper_bgcolor='#1e293b',"),
    L("        title=dict(text=f'{q} \u2014 Feature radar (Musk responses)',"),
    L("                   font=dict(color='#e2e8f0', size=12)),"),
    L("        height=320, margin=dict(l=40,r=40,t=50,b=20))"),
    L("    return fig"),
    L(""),
    L("def arrow_cell(val, yoy, unavail=False):"),
    L("    if unavail or (isinstance(val, float) and np.isnan(val)):"),
    L("        return '<span class=\"ag-na\">n/a</span>'"),
    L("    yoy_str = ''"),
    L("    if yoy is not None and not (isinstance(yoy, float) and np.isnan(yoy)):"),
    L("        if yoy > 2:"),
    L("            yoy_str = f' <span class=\"ag-arrow-up\">\u2191{yoy:.1f}%</span>'"),
    L("        elif yoy < -2:"),
    L("            yoy_str = f' <span class=\"ag-arrow-down\">\u2193{abs(yoy):.1f}%</span>'"),
    L("        else:"),
    L("            yoy_str = ' <span class=\"ag-arrow-flat\">\u2192</span>'"),
    L("    return f'{val:,.0f}{yoy_str}'"),
    L(""),
    L("def _c(row, col, yoy_col):"),
    L("    v = row.get(col)"),
    L("    unavail = bool(row.get(f'{col}_unavailable', pd.isna(v) if v is not None else True))"),
    L("    if pd.isna(v): return '<span class=\"ag-na\">n/a</span>'"),
    L("    yoy = row.get(yoy_col)"),
    L("    return arrow_cell(v, yoy if (yoy is not None and not pd.isna(yoy)) else None, unavail)"),
    L(""),
    L("def build_gaap_table(fy):"),
    L("    rows = GAAP[GAAP['fy'] == fy]"),
    L("    if len(rows) == 0: return '<p>No GAAP data for this year.</p>'"),
    L("    r = rows.iloc[0].to_dict()"),
    L("    gm = r.get('gross_margin_pct','')"),
    L("    gm_str = f'{gm:.1f}%' if isinstance(gm, float) and not np.isnan(gm) else 'n/a'"),
    L("    body = ("),
    L("        f'<tr><td>Total Revenue (USD m)</td><td>{_c(r,\"total_revenue\",\"total_revenue_yoy_pct\")}</td></tr>'"),
    L("        f'<tr><td>Gross Profit (USD m)</td><td>{_c(r,\"gross_profit\",\"gross_margin_pct_yoy_pct\")}</td></tr>'"),
    L("        f'<tr><td>Gross Margin %</td><td>{gm_str}</td></tr>'"),
    L("        f'<tr><td>Operating Income (USD m)</td><td>{_c(r,\"operating_income\",\"operating_income_yoy_pct\")}</td></tr>'"),
    L("        f'<tr><td>Net Income (USD m)</td><td>{_c(r,\"net_income\",\"net_income_yoy_pct\")}</td></tr>'"),
    L("        f'<tr><td>EPS Diluted</td><td>{_c(r,\"eps_diluted\",\"eps_diluted_yoy_pct\")}</td></tr>'"),
    L("    )"),
    L("    return (f'<table class=\"ag-table\"><tr><th>GAAP Metric \u2014 FY{fy}</th>'"),
    L("            f'<th>Value (YoY)</th></tr>{body}</table>')"),
    L(""),
    L("def build_kpi_table(fy):"),
    L("    rows = KPI[KPI['fy'] == fy]"),
    L("    if len(rows) == 0: return '<p>No KPI data.</p>'"),
    L("    r = rows.iloc[0].to_dict()"),
    L("    sc = '<span class=\"ag-na\">n/a \u2014 not reported in 10-K</span>'"),
    L("    body = ("),
    L("        f'<tr><td>Vehicle Deliveries</td><td>{_c(r,\"vehicle_deliveries\",\"vehicle_deliveries_yoy_pct\")}</td></tr>'"),
    L("        f'<tr><td>Vehicle Production</td><td>{_c(r,\"vehicle_production\",\"vehicle_production_yoy_pct\")}</td></tr>'"),
    L("        f'<tr><td>Energy Storage (GWh)</td><td>{_c(r,\"energy_storage_gwh\",\"energy_storage_gwh_yoy_pct\")}</td></tr>'"),
    L("        f'<tr><td>Solar Deployed (MW)</td><td>{_c(r,\"solar_deployed_mw\",\"solar_deployed_mw_yoy_pct\")}</td></tr>'"),
    L("        f'<tr><td>Supercharger Stations</td><td>{sc}</td></tr>'"),
    L("        f'<tr><td>Supercharger Connectors</td><td>{sc}</td></tr>'"),
    L("    )"),
    L("    return (f'<table class=\"ag-table\"><tr><th>Non-financial KPI \u2014 FY{fy}</th>'"),
    L("            f'<th>Value (YoY)</th></tr>{body}</table>')"),
    L(""),
    L("print('Utilities ready.')"),
], hidden=True, title="\U0001f527 Utilities"))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 3 — Introduction (markdown)
# ═══════════════════════════════════════════════════════════════════════════════
intro_html = (
    "<div style='background:#0f172a;padding:28px 32px;border-radius:10px;"
    "border:1px solid #334155;font-family:Georgia,serif;color:#e2e8f0;'>\n"
    "<h1 style='color:#818cf8;margin:0 0 6px 0;font-size:1.8em;'>The Analyst&#8217;s Edge</h1>\n"
    "<h2 style='color:#94a3b8;margin:0 0 20px 0;font-weight:normal;font-size:1.1em;'>"
    "Multimodal Analysis of Tesla Earnings Calls &nbsp;&middot;&nbsp; AG952 Week 10</h2>\n"
    "<p style='line-height:1.8;margin-bottom:14px;'>It is the morning after a Tesla earnings call. "
    "You are a buy-side analyst at a mid-size asset manager. Your portfolio manager is waiting for "
    "your note before the market opens. You have three sources of evidence: the text of the Q&amp;A "
    "session, a set of infographics from the most recent annual report, and acoustic measurements of "
    "Elon Musk&#8217;s voice during the call. Your task is to integrate these signals and make a "
    "prediction about how the market responded over the five trading days that followed.</p>\n"
    "<p style='line-height:1.8;margin-bottom:14px;'>You will work through three rounds, each "
    "introducing one new modality. In each round you will update your prediction and, crucially, "
    "explain your reasoning. At the end, the actual outcomes are revealed and the team whose "
    "predictions and reasoning best withstand the evidence wins the session.</p>\n"
    "<p style='line-height:1.8;color:#94a3b8;font-size:0.92em;margin:0;'>"
    "<strong style='color:#e2e8f0;'>Four earnings calls</strong> have been selected from the "
    "Tesla transcript archive (2022&#8211;2024). You will analyse each call in turn. Your "
    "predictions are locked after submission and remain hidden from other teams until all teams "
    "in the session have submitted that round.</p>\n"
    "</div>\n"
)
cells.append(md_cell([intro_html]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 4 — Team registration
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(code_cell([
    L("display(HTML('<div class=\"ag-section-hdr\">Step 1 of 4 &nbsp;&middot;&nbsp; Register your team</div>'))"),
    L("team_input = widgets.Text(placeholder='e.g. Team Hawkins',"),
    L("    description='Team name:', layout=widgets.Layout(width='340px'),"),
    L("    style={'description_width': '90px'})"),
    L("reg_btn    = widgets.Button(description='Register', button_style='primary',"),
    L("    layout=widgets.Layout(width='120px'))"),
    L("reg_status = widgets.HTML()"),
    L(""),
    L("def on_register(b):"),
    L("    name = team_input.value.strip()"),
    L("    if not name:"),
    L("        reg_status.value = '<span style=\"color:#ef4444;\">Please enter a team name.</span>'"),
    L("        return"),
    L("    STATE['team_name'] = name"),
    L("    try:"),
    L("        resp = post_to_script({'action':'register_team','team_name':name})"),
    L("        msg = 'already registered' if resp.get('message')=='already_registered' else 'registered'"),
    L("        if resp.get('success'):"),
    L("            STATE['registered'] = True"),
    L("            reg_status.value = (f'<span style=\"color:#22c55e;\">\u2713 <strong>{name}</strong>'"),
    L("                                f' {msg}. You are ready to begin.</span>')"),
    L("            team_input.disabled = True; reg_btn.disabled = True"),
    L("        else:"),
    L("            reg_status.value = f'<span style=\"color:#ef4444;\">Registration failed.</span>'"),
    L("    except Exception:"),
    L("        STATE['registered'] = True"),
    L("        reg_status.value = (f'<span style=\"color:#f59e0b;\">\u26a0 Offline mode \u2014 '"),
    L("                            f'team name saved locally as <strong>{name}</strong>.</span>')"),
    L(""),
    L("reg_btn.on_click(on_register)"),
    L("display(widgets.HBox([team_input, reg_btn]))"),
    L("display(reg_status)"),
]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 5 — Stock timeline + colour legend
# ═══════════════════════════════════════════════════════════════════════════════
legend_html = (
    "<div style='background:#1e293b;border:1px solid #334155;border-radius:8px;"
    "padding:14px 20px;margin:12px 0;font-family:Georgia,serif;'>\n"
    "<p style='color:#818cf8;margin:0 0 10px 0;font-weight:bold;'>"
    "Colour grammar &#8212; consistent throughout this notebook</p>\n"
    "<table style='border-collapse:collapse;'>\n"
    "<tr><td style='padding:4px 16px 4px 0;'>"
    "<span style='background:#22c55e;padding:3px 10px;border-radius:4px;color:#fff;"
    "font-size:0.85em;'>&#9632; Green</span></td>"
    "<td style='color:#e2e8f0;font-size:0.88em;padding:4px 0;'>"
    "LM positive sentiment &nbsp;|&nbsp; Positive stock return</td></tr>\n"
    "<tr><td style='padding:4px 16px 4px 0;'>"
    "<span style='background:#ef4444;padding:3px 10px;border-radius:4px;color:#fff;"
    "font-size:0.85em;'>&#9632; Red</span></td>"
    "<td style='color:#e2e8f0;font-size:0.88em;'>"
    "LM negative sentiment &nbsp;|&nbsp; Negative stock return</td></tr>\n"
    "<tr><td style='padding:4px 16px 4px 0;'>"
    "<span style='background:#9ca3af;padding:3px 10px;border-radius:4px;color:#fff;"
    "font-size:0.85em;'>&#9632; Grey</span></td>"
    "<td style='color:#e2e8f0;font-size:0.88em;'>LM neutral sentiment</td></tr>\n"
    "<tr><td style='padding:4px 16px 4px 0;'>"
    "<span style='background:#f59e0b;padding:3px 10px;border-radius:4px;color:#fff;"
    "font-size:0.85em;'>&#9632; Amber</span></td>"
    "<td style='color:#e2e8f0;font-size:0.88em;'>"
    "Above-average fraction of unvoiced (more silence / hesitation)</td></tr>\n"
    "<tr><td style='padding:4px 16px 4px 0;'>"
    "<span style='background:#3b82f6;padding:3px 10px;border-radius:4px;color:#fff;"
    "font-size:0.85em;'>&#9632; Blue</span></td>"
    "<td style='color:#e2e8f0;font-size:0.88em;'>"
    "Below-average fraction of unvoiced (more voiced / confident)</td></tr>\n"
    "</table>\n"
    "<p style='color:#94a3b8;font-size:0.82em;margin:10px 0 0 0;'>"
    "<strong style='color:#e2e8f0;'>Chip allocation:</strong> You have 12 chips split across "
    "four calls. Allocate 1, 2, or 3 chips per call before submitting Round 1. Higher allocation "
    "amplifies your score for that call. You may shift one chip each in Rounds 2 and 3.</p>\n"
    "</div>\n"
)
cells.append(code_cell([
    L("display(HTML('<div class=\"ag-section-hdr\">Tesla stock price 2021&#8211;2024</div>'))"),
    L("try:"),
    L("    display(Image(filename=f'{DRIVE_ROOT}/TSLA_price_timeline.png', width=900))"),
    L("except Exception:"),
    L("    display(HTML('<p style=\"color:#94a3b8;\">Timeline image not found.</p>'))"),
    L("display(HTML(", repr(legend_html), "))"),
]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 6 — Round 1 header (markdown)
# ═══════════════════════════════════════════════════════════════════════════════
r1_hdr = (
    "<div style='background:linear-gradient(90deg,#1e1b4b,#0f172a);padding:18px 24px;"
    "border-radius:8px;border-left:4px solid #818cf8;margin:20px 0 12px 0;"
    "font-family:Georgia,serif;'>\n"
    "<h2 style='color:#818cf8;margin:0 0 4px 0;'>Round 1 &#8212; The Text</h2>\n"
    "<p style='color:#94a3b8;margin:0;font-size:0.95em;'>Read the Q&amp;A excerpts below. "
    "Use only the text to make your first predictions. Each excerpt shows the "
    "highest-divergence question-answer pair from the call transcript.</p>\n"
    "</div>\n"
)
cells.append(md_cell([r1_hdr]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 7 — Round 1: Four call cards (2x2 grid)
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(code_cell([
    L("def make_card_html(c):"),
    L("    q, exc = c['quarter'], c['excerpt']"),
    L("    mt = exc['musk_text'][:600] + ('\u2026' if len(exc['musk_text'])>600 else '')"),
    L("    net = exc['musk_net_sent']"),
    L("    if net > 0.005:   gauge_cls, gauge_sym = 'ag-gauge-pos', f'+{net:.3f}'"),
    L("    elif net < -0.005: gauge_cls, gauge_sym = 'ag-gauge-neg', f'{net:.3f}'"),
    L("    else:              gauge_cls, gauge_sym = 'ag-gauge-neu', f'{net:.3f}'"),
    L("    gauge_lbl = ('net positive' if net>0.005 else 'net negative' if net<-0.005"),
    L("                 else 'near-neutral') + ' sentiment'"),
    L("    return ("),
    L("        f'<div class=\"ag-card\" style=\"min-height:260px;\">'"),
    L("        f'<h4>{q} &nbsp;<span style=\"color:#94a3b8;font-size:0.8em;font-weight:normal;\">'"),
    L("        f'{c[\"call_date\"]}</span></h4>'"),
    L("        f'<div class=\"ag-label\">Analyst: {exc[\"analyst_speaker\"]}</div>'"),
    L("        f'<div class=\"ag-excerpt-box\">'"),
    L("        f'<span class=\"ag-label\">Q &nbsp;</span>'"),
    L("        f'<span class=\"ag-analyst\">{exc[\"analyst_text\"][:400]}</span><br/><br/>'"),
    L("        f'<span class=\"ag-label\">A &nbsp;</span>'"),
    L("        f'<span class=\"ag-musk\">{mt}</span></div>'"),
    L("        f'<div style=\"margin-top:8px;\">'"),
    L("        f'<span class=\"ag-label\">Aggregate LM sentiment (Musk) &nbsp;</span>'"),
    L("        f'<span class=\"{gauge_cls}\">{gauge_sym}</span>'"),
    L("        f'<span style=\"color:#94a3b8;font-size:0.82em;\"> &nbsp; {gauge_lbl}</span>'"),
    L("        f'</div></div>'"),
    L("    )"),
    L(""),
    L("def make_sent_chart(c):"),
    L("    out = widgets.Output()"),
    L("    exc = c['excerpt']"),
    L("    with out:"),
    L("        fig, axes = plt.subplots(1, 2, figsize=(8, 2.2))"),
    L("        fig.patch.set_facecolor('#1e293b')"),
    L("        render_sentiment_bars(axes[0], exc['analyst_sentences'], 'Analyst (sentence LM)')"),
    L("        render_sentiment_bars(axes[1], exc['musk_sentences'],    'Musk (sentence LM)')"),
    L("        plt.tight_layout(pad=0.5); plt.show(); plt.close()"),
    L("    return out"),
    L(""),
    L("cards = [widgets.VBox([widgets.HTML(value=make_card_html(c)), make_sent_chart(c)])"),
    L("         for c in CALLS]"),
    L("grid  = widgets.GridBox(cards, layout=widgets.Layout("),
    L("    grid_template_columns='repeat(2, 1fr)', grid_gap='8px', width='100%'))"),
    L("display(grid)"),
]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 8 — Round 1 submission panel
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(code_cell([
    L("display(HTML('<div class=\"ag-section-hdr\">Round 1 &#8212; Submit your predictions</div>'))"),
    L("chip_sliders   = {}"),
    L("pred_dropdowns = {}"),
    L("reason_areas   = {}"),
    L("word_counters  = {}"),
    L(""),
    L("for _c in CALLS:"),
    L("    _q = _c['quarter']"),
    L("    chip_sliders[_q] = widgets.IntSlider(value=3, min=1, max=3, step=1,"),
    L("        description=f'{_q} chips:', style={'description_width':'110px'},"),
    L("        layout=widgets.Layout(width='320px'))"),
    L("    pred_dropdowns[_q] = widgets.Dropdown("),
    L("        options=['-- select --', 'Stock rose', 'Stock fell'],"),
    L("        description=f'{_q}:', style={'description_width':'80px'},"),
    L("        layout=widgets.Layout(width='240px'))"),
    L("    reason_areas[_q] = widgets.Textarea("),
    L("        placeholder='Your rationale (max 30 words) \u2026',"),
    L("        layout=widgets.Layout(width='400px', height='64px'))"),
    L("    word_counters[_q] = widgets.HTML(value='<div class=\"ag-word-counter\">0 / 30 words</div>')"),
    L("    def _mk_wc(_q_=_q):"),
    L("        def _upd(ch):"),
    L("            wc = len(ch['new'].split())"),
    L("            col = '#ef4444' if wc > 30 else '#94a3b8'"),
    L("            word_counters[_q_].value = (f'<div class=\"ag-word-counter\" '"),
    L("                f'style=\"color:{col};\">{wc} / 30 words</div>')"),
    L("        return _upd"),
    L("    reason_areas[_q].observe(_mk_wc(), names='value')"),
    L(""),
    L("rows_w = []"),
    L("for _c in CALLS:"),
    L("    _q = _c['quarter']"),
    L("    rows_w.append(widgets.HBox(["),
    L("        widgets.VBox(["),
    L("            widgets.HTML(value=f'<b style=\"color:#818cf8;\">{_q}</b>'),"),
    L("            chip_sliders[_q], pred_dropdowns[_q]],"),
    L("            layout=widgets.Layout(width='360px')),"),
    L("        widgets.VBox(["),
    L("            widgets.HTML(value='<span style=\"color:#94a3b8;font-size:0.85em;\">Rationale:</span>'),"),
    L("            reason_areas[_q], word_counters[_q]])],"),
    L("        layout=widgets.Layout(border='1px solid #334155', padding='10px',"),
    L("                              margin='4px 0', border_radius='6px')))"),
    L("display(widgets.VBox(rows_w))"),
    L(""),
    L("chip_total_disp = widgets.HTML()"),
    L("def _upd_chips(*args):"),
    L("    tot = sum(chip_sliders[q].value for q in QUARTERS)"),
    L("    col = '#22c55e' if tot == 12 else '#ef4444'"),
    L("    chip_total_disp.value = ("),
    L("        f'<div style=\"font-family:Georgia;margin:6px 0;\">Total chips: '"),
    L("        f'<span style=\"color:{col};font-weight:bold;\">{tot}</span> / 12'"),
    L("        f'{\" \u2713\" if tot==12 else \" \u2014 must equal 12\"}</div>')"),
    L("for q in QUARTERS: chip_sliders[q].observe(_upd_chips, names='value')"),
    L("_upd_chips(); display(chip_total_disp)"),
    L(""),
    L("r1_submit_btn = widgets.Button(description='Submit Round 1',"),
    L("    button_style='success', layout=widgets.Layout(width='200px', height='38px'))"),
    L("r1_status = widgets.HTML()"),
    L("r1_status_box = widgets.Output()"),
    L(""),
    L("def on_r1_submit(b):"),
    L("    if not STATE.get('team_name'):"),
    L("        r1_status.value = '<span style=\"color:#ef4444;\">Register your team first.</span>'; return"),
    L("    if STATE.get('r1_submitted'):"),
    L("        r1_status.value = '<span style=\"color:#f59e0b;\">Already submitted.</span>'; return"),
    L("    tot = sum(chip_sliders[q].value for q in QUARTERS)"),
    L("    if tot != 12:"),
    L("        r1_status.value = f'<span style=\"color:#ef4444;\">Chip total is {tot}; must equal 12.</span>'; return"),
    L("    for q in QUARTERS:"),
    L("        if pred_dropdowns[q].value == '-- select --':"),
    L("            r1_status.value = f'<span style=\"color:#ef4444;\">Select prediction for {q}.</span>'; return"),
    L("        wc = len(reason_areas[q].value.split())"),
    L("        if wc == 0:"),
    L("            r1_status.value = f'<span style=\"color:#ef4444;\">Enter rationale for {q}.</span>'; return"),
    L("        if wc > 30:"),
    L("            r1_status.value = f'<span style=\"color:#ef4444;\">{q}: rationale over 30 words ({wc}).</span>'; return"),
    L("    STATE['chips'] = {q: chip_sliders[q].value for q in QUARTERS}"),
    L("    payload = {'action':'submit_round1','team_name':STATE['team_name'],"),
    L("               'calls':[{'quarter':q,'chips':chip_sliders[q].value,"),
    L("                          'prediction':pred_dropdowns[q].value,"),
    L("                          'reasoning':reason_areas[q].value.strip()} for q in QUARTERS]}"),
    L("    try:"),
    L("        resp = post_to_script(payload)"),
    L("        if not resp.get('success'):"),
    L("            r1_status.value = f'<span style=\"color:#ef4444;\">Error: {resp.get(\"message\")}</span>'; return"),
    L("    except Exception: pass"),
    L("    STATE['r1_submitted'] = True"),
    L("    for q in QUARTERS:"),
    L("        chip_sliders[q].disabled=True; pred_dropdowns[q].disabled=True"),
    L("        reason_areas[q].disabled=True"),
    L("    r1_submit_btn.disabled = True"),
    L("    r1_status.value = '<span style=\"color:#22c55e;\">\u2713 Round 1 submitted.</span>'"),
    L("    with r1_status_box:"),
    L("        try:"),
    L("            st = get_status(1)"),
    L("            sub = st.get('submitted_teams', [])"),
    L("            display(HTML(f'<div class=\"ag-status-box\">Teams submitted: '"),
    L("                         f'<b style=\"color:#22c55e;\">{len(sub)}</b> / {st.get(\"total\",\"?\")}"),
    L("                         f'<br/>{\"  \".join(sub)}</div>'))"),
    L("        except Exception: pass"),
    L(""),
    L("r1_submit_btn.on_click(on_r1_submit)"),
    L("display(widgets.HBox([r1_submit_btn, r1_status]))"),
    L("display(r1_status_box)"),
]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 9 — Round 2 header (markdown)
# ═══════════════════════════════════════════════════════════════════════════════
r2_hdr = (
    "<div style='background:linear-gradient(90deg,#1e1b4b,#0f172a);padding:18px 24px;"
    "border-radius:8px;border-left:4px solid #f59e0b;margin:20px 0 12px 0;"
    "font-family:Georgia,serif;'>\n"
    "<h2 style='color:#f59e0b;margin:0 0 4px 0;'>Round 2 &#8212; The Images</h2>\n"
    "<p style='color:#94a3b8;margin:0;font-size:0.95em;'>Each tab below shows the retained "
    "infographics from Tesla&#8217;s annual report for the year preceding each earnings call, "
    "alongside a signal divergence panel. Classify each call&#8217;s signal and optionally "
    "shift one chip before submitting.</p>\n"
    "</div>\n"
)
cells.append(md_cell([r2_hdr]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 10 — Round 2: Tab content
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(code_cell([
    L("def make_r2_tab(c):"),
    L("    q, fy = c['quarter'], c['10k_fy']"),
    L("    imgs_df = IMG_MFST[q]"),
    L("    gallery = []"),
    L("    for _, row in imgs_df.iterrows():"),
    L("        img_path = row.get('filepath', row.get('path', ''))"),
    L("        imputed_note = ('<br/><span style=\"color:#f59e0b;font-size:0.72em;\">'"),
    L("            '\u21b3 supplemented from adjacent year</span>' if row.get('imputed') else '')"),
    L("        card_html = ("),
    L("            '<div style=\"display:inline-block;background:#0f172a;border:1px solid #334155;'"),
    L("            'border-radius:6px;padding:8px;margin:6px;vertical-align:top;max-width:280px;\">'"),
    L("            f'<div style=\"color:#818cf8;font-size:0.8em;margin-bottom:4px;\">'"),
    L("            f'{row.get(\"image_type\",\"Unknown\")}</div>'"),
    L("            f'<div style=\"color:#94a3b8;font-size:0.75em;\">{row.get(\"data_content\",\"\")}</div>'"),
    L("            f'<div style=\"color:#475569;font-size:0.72em;\">{row.get(\"section\",\"\")}</div>'"),
    L("            f'{imputed_note}</div>'"),
    L("        )"),
    L("        item = [widgets.HTML(value=card_html)]"),
    L("        try:"),
    L("            if img_path and Path(img_path).exists():"),
    L("                item.insert(0, widgets.Image(value=open(img_path,'rb').read(),"),
    L("                    format='png', layout=widgets.Layout(max_width='260px', max_height='180px')))"),
    L("        except Exception: pass"),
    L("        gallery.append(widgets.VBox(item, layout=widgets.Layout(margin='4px')))"),
    L("    gallery_box = widgets.HBox(gallery, layout=widgets.Layout(flex_flow='row wrap'))"),
    L("    div_html = ("),
    L("        f'<div style=\"font-family:Georgia,serif;\">'"),
    L("        f'<div style=\"color:#818cf8;font-size:0.9em;margin-bottom:8px;\">'"),
    L("        f'What Tesla reported vs what Tesla showed \u2014 FY{fy}</div>'"),
    L("        f'<div style=\"display:grid;grid-template-columns:1fr 1fr;gap:12px;\">'"),
    L("        f'<div>{build_gaap_table(fy)}</div>'"),
    L("        f'<div>{build_kpi_table(fy)}</div>'"),
    L("        f'</div></div>'"),
    L("    )"),
    L("    cls_w = widgets.RadioButtons("),
    L("        options=["),
    L("            'A \u2014 Consistent: text, images, and numbers point the same way',"),
    L("            'B \u2014 Divergent: at least one signal contradicts the others',"),
    L("            'C \u2014 Unclear: insufficient information to classify'],"),
    L("        description='Signal:', style={'description_width':'60px'},"),
    L("        layout=widgets.Layout(width='98%'))"),
    L("    return widgets.VBox(["),
    L("        widgets.HTML(value='<div class=\"ag-label\" style=\"margin:6px 0 4px 0;\">Infographics</div>'),"),
    L("        gallery_box,"),
    L("        widgets.HTML(value='<hr style=\"border-color:#334155;margin:10px 0;\">'),"),
    L("        widgets.HTML(value=div_html),"),
    L("        widgets.HTML(value='<div class=\"ag-label\" style=\"margin:12px 0 4px 0;\">Signal classification</div>'),"),
    L("        cls_w,"),
    L("    ], layout=widgets.Layout(padding='10px')), cls_w"),
    L(""),
    L("r2_tab      = widgets.Tab()"),
    L("r2_classify = {}"),
    L("_tab_contents = []"),
    L("for _c in CALLS:"),
    L("    _content, _cls = make_r2_tab(_c)"),
    L("    _tab_contents.append(_content)"),
    L("    r2_classify[_c['quarter']] = _cls"),
    L("r2_tab.children = _tab_contents"),
    L("for _i, _c in enumerate(CALLS):"),
    L("    r2_tab.set_title(_i, _c['quarter'])"),
    L("display(r2_tab)"),
]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 11 — Round 2: Chip shift + submit
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(code_cell([
    L("display(HTML('<div class=\"ag-section-hdr\">Round 2 &#8212; Optional chip shift &amp; submission</div>'))"),
    L("shift_from   = widgets.Dropdown(options=QUARTERS, description='Move 1 chip from:',"),
    L("    style={'description_width':'140px'})"),
    L("shift_to     = widgets.Dropdown(options=QUARTERS, description='to:',"),
    L("    style={'description_width':'30px'})"),
    L("shift_btn    = widgets.Button(description='Confirm shift', button_style='warning',"),
    L("    layout=widgets.Layout(width='140px'))"),
    L("shift_status = widgets.HTML()"),
    L(""),
    L("def on_shift_r2(b):"),
    L("    if STATE.get('r2_chip_shift_used'):"),
    L("        shift_status.value = '<span style=\"color:#f59e0b;\">Shift already used.</span>'; return"),
    L("    src, dst = shift_from.value, shift_to.value"),
    L("    if src == dst:"),
    L("        shift_status.value = '<span style=\"color:#ef4444;\">Source and destination must differ.</span>'; return"),
    L("    if STATE['chips'][src] <= 1:"),
    L("        shift_status.value = f'<span style=\"color:#ef4444;\">{src} at minimum.</span>'; return"),
    L("    if STATE['chips'][dst] >= 3:"),
    L("        shift_status.value = f'<span style=\"color:#ef4444;\">{dst} at maximum.</span>'; return"),
    L("    STATE['chips'][src] -= 1; STATE['chips'][dst] += 1"),
    L("    STATE['r2_chip_shift_used'] = True"),
    L("    shift_btn.disabled=True; shift_from.disabled=True; shift_to.disabled=True"),
    L("    shift_status.value = (f'<span style=\"color:#22c55e;\">\u2713 Moved 1 chip: '"),
    L("        f'{src}\u2192{dst}. New allocation: {STATE[\"chips\"]}</span>')"),
    L(""),
    L("shift_btn.on_click(on_shift_r2)"),
    L("display(widgets.HTML('<p style=\"font-family:Georgia;color:#94a3b8;font-size:0.88em;\">'"),
    L("    'You may move 1 chip once this round. Optional and irreversible.</p>'))"),
    L("display(widgets.HBox([shift_from, shift_to, shift_btn])); display(shift_status)"),
    L(""),
    L("r2_submit_btn = widgets.Button(description='Submit Round 2', button_style='success',"),
    L("    layout=widgets.Layout(width='200px', height='38px'))"),
    L("r2_status     = widgets.HTML()"),
    L("r2_status_box = widgets.Output()"),
    L(""),
    L("def on_r2_submit(b):"),
    L("    if not STATE.get('r1_submitted'):"),
    L("        r2_status.value = '<span style=\"color:#ef4444;\">Submit Round 1 first.</span>'; return"),
    L("    if STATE.get('r2_submitted'):"),
    L("        r2_status.value = '<span style=\"color:#f59e0b;\">Already submitted.</span>'; return"),
    L("    payload = {'action':'submit_round2','team_name':STATE['team_name'],"),
    L("               'calls':[{'quarter':q,'classification':r2_classify[q].value}"),
    L("                         for q in QUARTERS]}"),
    L("    try:"),
    L("        resp = post_to_script(payload)"),
    L("        if not resp.get('success'):"),
    L("            r2_status.value = f'<span style=\"color:#ef4444;\">{resp.get(\"message\")}</span>'; return"),
    L("    except Exception: pass"),
    L("    STATE['r2_submitted'] = True"),
    L("    for q in QUARTERS: r2_classify[q].disabled = True"),
    L("    r2_submit_btn.disabled=True; shift_btn.disabled=True"),
    L("    r2_status.value = '<span style=\"color:#22c55e;\">\u2713 Round 2 submitted.</span>'"),
    L("    with r2_status_box:"),
    L("        try:"),
    L("            st = get_status(2); sub = st.get('submitted_teams',[])"),
    L("            display(HTML(f'<div class=\"ag-status-box\">Round 2 submissions: '"),
    L("                f'<b style=\"color:#22c55e;\">{len(sub)}</b>/{st.get(\"total\",\"?\")}"),
    L("                f'<br/>{\"  \".join(sub)}</div>'))"),
    L("        except Exception: pass"),
    L(""),
    L("r2_submit_btn.on_click(on_r2_submit)"),
    L("display(widgets.HBox([r2_submit_btn, r2_status])); display(r2_status_box)"),
]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 12 — Round 3 header (markdown)
# ═══════════════════════════════════════════════════════════════════════════════
r3_hdr = (
    "<div style='background:linear-gradient(90deg,#1e1b4b,#0f172a);padding:18px 24px;"
    "border-radius:8px;border-left:4px solid #3b82f6;margin:20px 0 12px 0;"
    "font-family:Georgia,serif;'>\n"
    "<h2 style='color:#3b82f6;margin:0 0 4px 0;'>Round 3 &#8212; The Audio</h2>\n"
    "<p style='color:#94a3b8;margin:0;font-size:0.95em;'>Paralinguistic features extracted "
    "from Elon Musk&#8217;s voice during each call. The silence map shows how much of each "
    "5-minute window is unvoiced; the radar chart profiles nine vocal dimensions against the "
    "cross-call average.</p>\n"
    "</div>\n"
)
cells.append(md_cell([r3_hdr]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 13 — Round 3: Silence maps + radars
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(code_cell([
    L("r3_reason_areas = {}"),
    L("r3_word_cntrs   = {}"),
    L(""),
    L("for _c in CALLS:"),
    L("    _q = _c['quarter']"),
    L("    display(HTML(f'<div class=\"ag-section-hdr\" style=\"border-left-color:#3b82f6;\">'"),
    L("                 f'{_q} &nbsp;&middot;&nbsp; {_c[\"call_date\"]}</div>'))"),
    L("    make_silence_map(_c).show()"),
    L("    make_radar(_c).show()"),
    L("    r3_reason_areas[_q] = widgets.Textarea("),
    L("        placeholder=f'Update or confirm your Round 1 rationale for {_q} (max 30 words) \u2026',"),
    L("        layout=widgets.Layout(width='720px', height='64px'))"),
    L("    r3_word_cntrs[_q] = widgets.HTML(value='<div class=\"ag-word-counter\">0 / 30 words</div>')"),
    L("    def _mk_wc3(_q_=_q):"),
    L("        def _upd(ch):"),
    L("            wc = len(ch['new'].split())"),
    L("            col = '#ef4444' if wc > 30 else '#94a3b8'"),
    L("            r3_word_cntrs[_q_].value = (f'<div class=\"ag-word-counter\" '"),
    L("                f'style=\"color:{col};\">{wc} / 30 words</div>')"),
    L("        return _upd"),
    L("    r3_reason_areas[_q].observe(_mk_wc3(), names='value')"),
    L("    display(widgets.HTML(f'<span style=\"color:#94a3b8;font-size:0.85em;\">'"),
    L("                          f'Update reasoning for {_q}:</span>'))"),
    L("    display(widgets.VBox([r3_reason_areas[_q], r3_word_cntrs[_q]]))"),
    L("    display(HTML('<hr style=\"border-color:#1e293b;margin:12px 0;\">'))"),
]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 14 — Round 3: Chip shift + final submit
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(code_cell([
    L("display(HTML('<div class=\"ag-section-hdr\" style=\"border-left-color:#3b82f6;\">'"),
    L("             'Round 3 &#8212; Optional chip shift &amp; final submission</div>'))"),
    L("r3_shift_from   = widgets.Dropdown(options=QUARTERS, description='Move 1 chip from:',"),
    L("    style={'description_width':'140px'})"),
    L("r3_shift_to     = widgets.Dropdown(options=QUARTERS, description='to:',"),
    L("    style={'description_width':'30px'})"),
    L("r3_shift_btn    = widgets.Button(description='Confirm shift', button_style='warning',"),
    L("    layout=widgets.Layout(width='140px'))"),
    L("r3_shift_status = widgets.HTML()"),
    L(""),
    L("def on_shift_r3(b):"),
    L("    if STATE.get('r3_chip_shift_used'):"),
    L("        r3_shift_status.value='<span style=\"color:#f59e0b;\">Shift already used.</span>'; return"),
    L("    src, dst = r3_shift_from.value, r3_shift_to.value"),
    L("    if src==dst:"),
    L("        r3_shift_status.value='<span style=\"color:#ef4444;\">Must differ.</span>'; return"),
    L("    if STATE['chips'][src] <= 1:"),
    L("        r3_shift_status.value=f'<span style=\"color:#ef4444;\">{src} at min.</span>'; return"),
    L("    if STATE['chips'][dst] >= 3:"),
    L("        r3_shift_status.value=f'<span style=\"color:#ef4444;\">{dst} at max.</span>'; return"),
    L("    STATE['chips'][src]-=1; STATE['chips'][dst]+=1"),
    L("    STATE['r3_chip_shift_used']=True"),
    L("    r3_shift_btn.disabled=True; r3_shift_from.disabled=True; r3_shift_to.disabled=True"),
    L("    r3_shift_status.value=(f'<span style=\"color:#22c55e;\">\u2713 Moved: '"),
    L("        f'{src}\u2192{dst}. Final chips: {STATE[\"chips\"]}</span>')"),
    L(""),
    L("r3_shift_btn.on_click(on_shift_r3)"),
    L("display(widgets.HBox([r3_shift_from, r3_shift_to, r3_shift_btn]))"),
    L("display(r3_shift_status)"),
    L(""),
    L("r3_submit_btn = widgets.Button(description='Submit Final Predictions',"),
    L("    button_style='success', layout=widgets.Layout(width='240px', height='38px'))"),
    L("r3_status     = widgets.HTML()"),
    L("r3_status_box = widgets.Output()"),
    L(""),
    L("def on_r3_submit(b):"),
    L("    if not STATE.get('r2_submitted'):"),
    L("        r3_status.value='<span style=\"color:#ef4444;\">Submit Round 2 first.</span>'; return"),
    L("    if STATE.get('r3_submitted'):"),
    L("        r3_status.value='<span style=\"color:#f59e0b;\">Already submitted.</span>'; return"),
    L("    for q in QUARTERS:"),
    L("        if len(r3_reason_areas[q].value.split()) > 30:"),
    L("            r3_status.value=f'<span style=\"color:#ef4444;\">{q} over 30 words.</span>'; return"),
    L("    payload = {'action':'submit_round3','team_name':STATE['team_name'],"),
    L("               'calls':[{'quarter':q,'chips':STATE['chips'][q],"),
    L("                          'prediction':pred_dropdowns[q].value,"),
    L("                          'reasoning':(r3_reason_areas[q].value.strip()"),
    L("                                       or reason_areas[q].value.strip())}"),
    L("                         for q in QUARTERS]}"),
    L("    try:"),
    L("        resp = post_to_script(payload)"),
    L("        if not resp.get('success'):"),
    L("            r3_status.value=f'<span style=\"color:#ef4444;\">{resp.get(\"message\")}</span>'; return"),
    L("    except Exception: pass"),
    L("    STATE['r3_submitted']=True"),
    L("    for q in QUARTERS: r3_reason_areas[q].disabled=True"),
    L("    r3_submit_btn.disabled=True; r3_shift_btn.disabled=True"),
    L("    r3_status.value='<span style=\"color:#22c55e;\">\u2713 Final predictions submitted. Scroll down for The Reveal.</span>'"),
    L("    with r3_status_box:"),
    L("        try:"),
    L("            st=get_status(3); sub=st.get('submitted_teams',[])"),
    L("            display(HTML(f'<div class=\"ag-status-box\">Final submissions: '"),
    L("                f'<b style=\"color:#22c55e;\">{len(sub)}</b>/{st.get(\"total\",\"?\")}"),
    L("                f'<br/>{\"  \".join(sub)}</div>'))"),
    L("        except Exception: pass"),
    L(""),
    L("r3_submit_btn.on_click(on_r3_submit)"),
    L("display(widgets.HBox([r3_submit_btn, r3_status])); display(r3_status_box)"),
]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 15 — Reveal header (markdown)
# ═══════════════════════════════════════════════════════════════════════════════
reveal_hdr = (
    "<div style='background:linear-gradient(90deg,#1e1b4b,#0f172a);padding:18px 24px;"
    "border-radius:8px;border-left:4px solid #22c55e;margin:20px 0 12px 0;"
    "font-family:Georgia,serif;'>\n"
    "<h2 style='color:#22c55e;margin:0 0 4px 0;'>The Reveal</h2>\n"
    "<p style='color:#94a3b8;margin:0;font-size:0.95em;'>"
    "Run this cell when the facilitator signals. The actual 5-day abnormal returns are "
    "displayed, predictions scored, and the debrief matrix shown.</p>\n"
    "</div>\n"
)
cells.append(md_cell([reveal_hdr]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 16 — Reveal: animated chart + scoring + debrief
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(code_cell([
    L("_qtrs   = [c['quarter'] for c in CALLS]"),
    L("_rets   = [c['returns']['abnormal_ret_pct'] for c in CALLS]"),
    L("_dirs   = [c['returns']['direction'] for c in CALLS]"),
    L("_colors = [CLR['ret_positive'] if d=='positive' else CLR['ret_negative'] for d in _dirs]"),
    L("_labels = [f\"{q}<br>{r:+.1f}%\" for q, r in zip(_qtrs, _rets)]"),
    L(""),
    L("_frames = [go.Frame("),
    L("    data=[go.Bar(x=_qtrs[:i+1], y=_rets[:i+1], text=_labels[:i+1],"),
    L("               textposition='outside', textfont=dict(color='#e2e8f0', size=11),"),
    L("               marker_color=_colors[:i+1])],"),
    L("    name=str(i)) for i in range(len(_qtrs))]"),
    L(""),
    L("_fig_reveal = go.Figure("),
    L("    data=[go.Bar(x=[], y=[], marker_color=[])],"),
    L("    frames=_frames,"),
    L("    layout=go.Layout("),
    L("        title=dict(text='5-Day Abnormal Returns \u2014 Actual Outcomes',"),
    L("                   font=dict(color='#e2e8f0', size=15)),"),
    L("        xaxis=dict(color='#94a3b8', gridcolor='#1e293b'),"),
    L("        yaxis=dict(title='Abnormal return (%)', color='#94a3b8',"),
    L("                   gridcolor='#1e293b', zeroline=True, zerolinecolor='#475569'),"),
    L("        plot_bgcolor='#0f172a', paper_bgcolor='#1e293b',"),
    L("        font=dict(color='#e2e8f0'), height=400,"),
    L("        updatemenus=[{'type':'buttons','showactive':False,"),
    L("            'buttons':[{'label':'\u25b6  Reveal','method':'animate',"),
    L("                'args':[None,{'frame':{'duration':1200,'redraw':True},"),
    L("                              'transition':{'duration':600},'fromcurrent':True}]}],"),
    L("            'x':0.5,'xanchor':'center','y':-0.12,'yanchor':'top'}]))"),
    L("_fig_reveal.show()"),
    L(""),
    L("# ── Scoring ──────────────────────────────────────────────────────────────────"),
    L("import time; time.sleep(0.3)"),
    L("display(HTML('<div class=\"ag-section-hdr\">Scoring</div>'))"),
    L(""),
    L("_score = 0"),
    L("_breakdown = []"),
    L("for _c in CALLS:"),
    L("    _q = _c['quarter']"),
    L("    _actual = _c['returns']['direction']"),
    L("    _pred   = pred_dropdowns[_q].value"),
    L("    _chips  = STATE['chips'][_q]"),
    L("    _ok = ((_pred=='Stock rose' and _actual=='positive') or"),
    L("           (_pred=='Stock fell' and _actual=='negative'))"),
    L("    _pts = _chips if _ok else -_chips"),
    L("    _score += _pts"),
    L("    _breakdown.append(dict(call=_q, prediction=_pred, actual=_actual,"),
    L("                           chips=_chips, pts=_pts, ok=_ok))"),
    L(""),
    L("_rows_html = ''"),
    L("for _b in _breakdown:"),
    L("    _col = '#22c55e' if _b['ok'] else '#ef4444'"),
    L("    _act_str = 'positive \u2191' if _b['actual']=='positive' else 'negative \u2193'"),
    L("    _rows_html += ("),
    L("        f'<tr><td>{_b[\"call\"]}</td><td>{_b[\"prediction\"]}</td>'"),
    L("        f'<td>{_act_str}</td><td>{_b[\"chips\"]}</td>'"),
    L("        f'<td style=\"color:{_col};\">{\"+\" if _b[\"ok\"] else \"\"}{_b[\"pts\"]}</td></tr>')"),
    L("_tot_col = '#22c55e' if _score >= 0 else '#ef4444'"),
    L("display(HTML("),
    L("    f'<table class=\"ag-table\">'"),
    L("    f'<tr><th>Call</th><th>Your prediction</th><th>Actual</th>'"),
    L("    f'<th>Chips</th><th>Points</th></tr>'"),
    L("    f'{_rows_html}'"),
    L("    f'<tr style=\"border-top:2px solid #334155;\">'"),
    L("    f'<td colspan=\"4\" style=\"text-align:right;color:#94a3b8;\">Total</td>'"),
    L("    f'<td style=\"color:{_tot_col};font-weight:bold;'>{\"+\" if _score>=0 else \"\"}{_score}</td></tr>'"),
    L("    f'</table>'))"),
    L(""),
    L("# ── Upset calls ───────────────────────────────────────────────────────────────"),
    L("_upset = [c['quarter'] for c in CALLS"),
    L("          if (c['excerpt']['musk_net_sent']>0.01 and c['returns']['direction']=='negative')"),
    L("          or (c['excerpt']['musk_net_sent']<-0.01 and c['returns']['direction']=='positive')]"),
    L("if _upset:"),
    L("    display(HTML("),
    L("        '<div style=\"background:#1e293b;border:1px solid #f59e0b;border-radius:8px;'"),
    L("        'padding:14px 20px;margin:12px 0;font-family:Georgia;\">'"),
    L("        '<p style=\"color:#f59e0b;margin:0 0 8px 0;font-weight:bold;\">'"),
    L("        f'Upset calls: {\", \".join(_upset)}</p>'"),
    L("        '<p style=\"color:#e2e8f0;font-size:0.9em;\">Calls where Musk\\'s LM sentiment '"),
    L("        'pointed in the opposite direction to the actual abnormal return. '"),
    L("        'These are where acoustic and visual signals carry the most information value.</p>'"),
    L("        '</div>'))"),
    L(""),
    L("# ── Debrief matrix ────────────────────────────────────────────────────────────"),
    L("display(HTML('<div class=\"ag-section-hdr\">Debrief matrix \u2014 signal coherence</div>'))"),
    L(""),
    L("_matrix_rows = ''"),
    L("for _c in CALLS:"),
    L("    _q      = _c['quarter']"),
    L("    _net    = _c['excerpt']['musk_net_sent']"),
    L("    _lm_dir = 'positive' if _net>0.005 else ('negative' if _net<-0.005 else 'neutral')"),
    L("    _row    = SUMMARY[SUMMARY['call']==f'TSLA_{_q}']"),
    L("    _fou    = _row['fraction_of_unvoiced_mean_musk'].values"),
    L("    _aco    = ('negative' if (len(_fou) and not np.isnan(_fou[0]) and _fou[0]>FOU_MEAN)"),
    L("               else 'positive' if len(_fou) else 'n/a')"),
    L("    _actual = _c['returns']['direction']"),
    L("    def _bg(sig, actual=_actual):"),
    L("        if sig in ('neutral','n/a'): return '#1e293b'"),
    L("        return '#14532d' if sig==actual else '#450a0a'"),
    L("    def _arr(sig):"),
    L("        if sig=='n/a':       return '<span class=\"ag-na\">n/a</span>'"),
    L("        if sig=='positive':  return '\u2191 positive'"),
    L("        if sig=='neutral':   return '\u2192 neutral'"),
    L("        return '\u2193 negative'"),
    L("    _act_col = '#22c55e' if _actual=='positive' else '#ef4444'"),
    L("    _matrix_rows += ("),
    L("        f'<tr><td style=\"color:#818cf8;font-weight:bold;\">{_q}</td>'"),
    L("        f'<td style=\"background:{_bg(_lm_dir)};\">{_arr(_lm_dir)}</td>'"),
    L("        f'<td style=\"background:{_bg(_aco)};\">{_arr(_aco)}</td>'"),
    L("        f'<td style=\"background:#1e293b;\"><span class=\"ag-na\">n/a</span></td>'"),
    L("        f'<td style=\"color:{_act_col};font-weight:bold;\">{_arr(_actual)}</td></tr>')"),
    L(""),
    L("display(HTML("),
    L("    '<p style=\"color:#94a3b8;font-size:0.85em;margin:4px 0 8px 0;\">'"),
    L("    'Green cell = signal matched outcome. Red = contradicted. '"),
    L("    'Images column shows n/a (EDGAR HTML cover photos only).</p>'"),
    L("    '<table class=\"ag-table\">'"),
    L("    '<tr><th>Call</th><th>Text (LM)</th><th>Audio (FoU)</th>'"),
    L("    '<th>Images</th><th>Actual outcome</th></tr>'"),
    L("    f'{_matrix_rows}'"),
    L("    '</table>'))"),
]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 17 — Individual reflection header (markdown)
# ═══════════════════════════════════════════════════════════════════════════════
refl_hdr = (
    "<div style='background:linear-gradient(90deg,#1e1b4b,#0f172a);padding:18px 24px;"
    "border-radius:8px;border-left:4px solid #94a3b8;margin:20px 0 12px 0;"
    "font-family:Georgia,serif;'>\n"
    "<h2 style='color:#94a3b8;margin:0 0 4px 0;'>Individual Reflection</h2>\n"
    "<p style='color:#94a3b8;margin:0;font-size:0.95em;'>"
    "This section is individual. Your responses are not shared with other teams "
    "and will not appear on the leaderboard. Submitted to a personal tab of the "
    "session spreadsheet, keyed by your team name and a timestamp.</p>\n"
    "</div>\n"
)
cells.append(md_cell([refl_hdr]))

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 18 — Individual reflection widgets
# ═══════════════════════════════════════════════════════════════════════════════
cells.append(code_cell([
    L("_questions = ["),
    L("    'Which modality (text, images, or audio) was most useful for predicting outcomes, and why?',"),
    L("    'Describe a call where the three modalities sent conflicting signals. How did you resolve the conflict?',"),
    L("    'If you were building an automated signal-extraction system for earnings calls, '"),
    L("    'which single feature would you prioritise and why?',"),
    L("]"),
    L("_ref_areas = [widgets.Textarea(placeholder=q,"),
    L("    layout=widgets.Layout(width='720px', height='90px')) for q in _questions]"),
    L(""),
    L("ref_submit_btn = widgets.Button(description='Submit reflection',"),
    L("    layout=widgets.Layout(width='200px'))"),
    L("ref_status = widgets.HTML()"),
    L(""),
    L("def on_ref_submit(b):"),
    L("    if not STATE.get('team_name'):"),
    L("        ref_status.value='<span style=\"color:#ef4444;\">Register first.</span>'; return"),
    L("    payload = {'action':'submit_reflection','team_name':STATE['team_name'],"),
    L("               'q1':_ref_areas[0].value.strip(),"),
    L("               'q2':_ref_areas[1].value.strip(),"),
    L("               'q3':_ref_areas[2].value.strip()}"),
    L("    try:"),
    L("        resp = post_to_script(payload)"),
    L("        if resp.get('success'):"),
    L("            ref_submit_btn.disabled=True"),
    L("            ref_status.value='<span style=\"color:#22c55e;\">\u2713 Reflection submitted.</span>'"),
    L("        else:"),
    L("            ref_status.value=f'<span style=\"color:#ef4444;\">{resp}</span>'"),
    L("    except Exception:"),
    L("        ref_submit_btn.disabled=True"),
    L("        ref_status.value='<span style=\"color:#f59e0b;\">\u26a0 Offline \u2014 thank you.</span>'"),
    L(""),
    L("ref_submit_btn.on_click(on_ref_submit)"),
    L(""),
    L("for _i, (_qlbl, _w) in enumerate(zip(_questions, _ref_areas), 1):"),
    L("    display(HTML(f'<div style=\"font-family:Georgia;color:#e2e8f0;margin:12px 0 4px 0;\">'"),
    L("                 f'{_i}. {_qlbl}</div>'))"),
    L("    display(_w)"),
    L("display(widgets.HBox([ref_submit_btn, ref_status]))"),
]))

# ═══════════════════════════════════════════════════════════════════════════════
# Write .ipynb
# ═══════════════════════════════════════════════════════════════════════════════
out_path = Path("/tmp/AG952/week10/AG952_Week10_Workshop.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

size_kb = out_path.stat().st_size // 1024
print(f"Written: {out_path}  ({size_kb} KB, {len(nb['cells'])} cells)")
