#!/usr/bin/env python3
"""Build AG952_Week10_Instructor.ipynb"""
import json

# ── helpers ───────────────────────────────────────────────────────────────────
def _mkcell(kind, src, title=None):
    if isinstance(src, str):
        lines = src.split('\n')
        while lines and lines[0] == '':
            lines.pop(0)
        while lines and lines[-1] == '':
            lines.pop()
        src = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines else [])
    if kind == 'code' and title:
        src = ['# @title ' + title + ' {display-mode: "form"}\n'] + src
    base = {'cell_type': kind, 'id': '', 'metadata': {}, 'source': src}
    if kind == 'code':
        base['execution_count'] = None
        base['outputs'] = []
    return base

def md(s):        return _mkcell('markdown', s)
def code(s, t=None): return _mkcell('code', s, t)

C = []

# ── Cell 0: Title ─────────────────────────────────────────────────────────────
C.append(md("""\
# AG952 Week 10 — Instructor Dashboard

Run **all cells** at the start of the workshop, then proceed top-to-bottom as each round closes.

| What | How |
|------|-----|
| Monitor progress | **Live Status** — refresh any time |
| Close a round early | **Force Unlock** button in each round section |
| See class analysis | **Fetch & Analyse** button — re-click to refresh after late submissions |
| Reveal scores | **Final Leaderboard** cell |

> Keep this notebook private — it requires your `INSTRUCTOR_KEY` and returns all team data."""))

# ── Cell 1: Config ────────────────────────────────────────────────────────────
C.append(code("""\
ENDPOINT       = "https://script.google.com/macros/s/AKfycbxnyxoAgcw5qdQk0m3nv4YX-orYcc6i_1yhm1tNNE10rHBYCD-vbwqCOp628kimi0qy/exec"
INSTRUCTOR_KEY = "AG952_2026"   # must match INSTRUCTOR_KEY in apps_script.js
DRIVE_ROOT     = "/content/drive/MyDrive/workshop_data/clips"
""", "⚙️ Configuration"))

# ── Cell 2: Setup ─────────────────────────────────────────────────────────────
C.append(code("""\
import json, re, time
from collections import Counter

import numpy as np
import pandas as pd
import requests
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output

display(HTML('''<style>
.inst-hdr{background:linear-gradient(90deg,#1e1b4b,#0f172a);padding:14px 20px;
  border-radius:8px;border-left:4px solid #f59e0b;margin:18px 0 10px 0;}
.inst-hdr h2{color:#f59e0b;margin:0 0 2px 0;font-family:Georgia,serif;font-size:1.2em;}
.inst-hdr p{color:#94a3b8;margin:0;font-size:0.87em;}
.stat-box{display:inline-block;background:#1e293b;border:1px solid #334155;
  border-radius:8px;padding:12px 20px;margin:5px;text-align:center;min-width:105px;}
.stat-box .n{font-size:1.9em;font-weight:bold;color:#f59e0b;display:block;line-height:1.1;}
.stat-box .l{font-size:0.78em;color:#94a3b8;}
.badge{display:inline-block;padding:2px 9px;border-radius:10px;
  font-size:0.78em;font-weight:bold;margin:2px;font-family:monospace;}
.b-wait{background:#431407;color:#fdba74;}
.ag-table{width:100%;border-collapse:collapse;font-family:Georgia,serif;
  font-size:0.9em;color:#e2e8f0;margin:8px 0;}
.ag-table th{color:#94a3b8;text-align:left;padding:6px 10px;border-bottom:1px solid #334155;}
.ag-table td{padding:6px 10px;border-bottom:1px solid #1e293b;}
.ag-table tr:hover td{background:#1e293b;}
</style>'''))

def _post(payload):
    try:
        r = requests.post(ENDPOINT, json=payload, timeout=20)
        return r.json()
    except Exception as exc:
        return {'success': False, 'error': str(exc)}

def get_status(rnd):
    return _post({'action': 'get_status', 'round': rnd})

def get_round_data(rnd):
    return _post({'action': 'get_round_data', 'round': rnd,
                  'instructor_key': INSTRUCTOR_KEY})

def do_force_unlock(rnd):
    return _post({'action': 'force_unlock_round', 'round': rnd,
                  'instructor_key': INSTRUCTOR_KEY})

def get_reflections():
    return _post({'action': 'get_reflections_data',
                  'instructor_key': INSTRUCTOR_KEY})

print('Setup complete.')
""", "📦 Setup"))

# ── Cell 3: Load manifest ─────────────────────────────────────────────────────
C.append(code("""\
from google.colab import drive
drive.mount('/content/drive', force_remount=False)

with open(f'{DRIVE_ROOT}/workshop_manifest.json') as _f:
    MANIFEST = json.load(_f)

CALLS    = MANIFEST['calls']
QUARTERS = [c['quarter'] for c in CALLS]
ANON_MAP = {'2024Q1': 'Call A', '2023Q1': 'Call B',
            '2022Q4': 'Call C', '2024Q2': 'Call D'}
ACTUALS  = {c['quarter']: c['returns']['direction'] for c in CALLS}

STOPWORDS = {
    'the','a','an','and','or','but','in','on','at','to','for','of','with',
    'is','was','it','this','that','i','we','our','their','be','as','by',
    'from','will','are','have','has','had','not','also','its','they','been',
    'stock','call','tesla','earnings','quarter','revenue','growth','market',
    'company','would','could','should','more','less','very','much','then',
    'when','than','so','if','just','get','into','after','before','about',
    'which','were','can','may','price','year','strong','weak','think',
    'expect','believe','see','show','one','two','three','new','high','low',
    'due','given','based','expected','reported','good','bad','well','still',
}

print(f'Manifest loaded — {len(CALLS)} calls')
for q in QUARTERS:
    act = ACTUALS[q]
    print(f'  {ANON_MAP.get(q,q):8s} ({q})  actual: {"up" if act=="positive" else "down"}')
""", "📋 Load Workshop Data"))

# ── Cell 4: Status dashboard ──────────────────────────────────────────────────
C.append(code("""\
def _build_status_html():
    html = '<div style="background:#0f172a;padding:16px;border-radius:10px;font-family:Georgia;">'
    statuses = {r: get_status(r) for r in [1, 2, 3]}
    s1      = statuses[1]
    n_teams = s1.get('total', 0) if s1.get('success') else '?'
    html += (f'<div class="stat-box"><span class="n">{n_teams}</span>'
             f'<span class="l">Teams registered</span></div>')
    for r in [1, 2, 3]:
        s = statuses[r]
        if s.get('success'):
            sub  = s['submitted_count']
            tot  = s['total']
            done = s['all_submitted']
            col  = '#22c55e' if done else ('#f59e0b' if sub > 0 else '#475569')
            lbl  = '&#10003; complete' if done else f'{sub}/{tot} in'
            html += (f'<div class="stat-box">'
                     f'<span class="n" style="color:{col};">{sub}/{tot}</span>'
                     f'<span class="l">Round {r} &#8212; {lbl}</span></div>')
    html += '<br style="clear:both;margin:4px 0;">'
    any_missing = False
    for r in [1, 2, 3]:
        s = statuses[r]
        if s.get('success') and s.get('not_submitted'):
            any_missing = True
            html += (f'<div style="margin:5px 0;color:#94a3b8;font-size:0.85em;">'
                     f'Round {r} &#8212; waiting on: ')
            for t in s['not_submitted']:
                html += f'<span class="badge b-wait">{t}</span>'
            html += '</div>'
    if not any_missing and n_teams != '?':
        html += '<div style="color:#22c55e;font-size:0.85em;margin-top:6px;">All teams up to date.</div>'
    html += (f'<div style="color:#475569;font-size:0.72em;margin-top:10px;'
             f'font-family:monospace;">Refreshed: {time.strftime("%H:%M:%S")}</div>')
    html += '</div>'
    return html

_st_out = widgets.Output()
_st_btn = widgets.Button(description='\\u21ba  Refresh Status', button_style='warning',
                          layout=widgets.Layout(width='165px'))

def _do_refresh(_b=None):
    with _st_out:
        clear_output(wait=True)
        display(HTML(_build_status_html()))

_st_btn.on_click(_do_refresh)
display(HTML('<div class="inst-hdr"><h2>Live Status Dashboard</h2>'
             '<p>Submission counts across all three rounds. '
             'Teams listed below are still outstanding.</p></div>'))
display(widgets.VBox([_st_btn, _st_out]))
_do_refresh()
""", "📊 Live Status Dashboard"))

# ── Cell 5: Round 1 ───────────────────────────────────────────────────────────
C.append(code("""\
display(HTML(
    '<div class="inst-hdr"><h2>Round 1 &#8212; Directional Predictions</h2>'
    '<p>Teams predict whether each call&#8217;s stock rose or fell and stake '
    'chips (1&#8211;3) as confidence. Leaderboard is hidden until you unlock.</p></div>'))

# ── Force Unlock ──────────────────────────────────────────────────────────────
_r1u_out = widgets.Output()
_r1u_btn = widgets.Button(description='\\U0001f513  Force Unlock Round 1',
                           button_style='danger',
                           layout=widgets.Layout(width='222px', height='38px'))

def _unlock_r1(b):
    _r1u_btn.disabled = True
    _r1u_btn.description = '\\u23f3  Unlocking...'
    resp = do_force_unlock(1)
    with _r1u_out:
        clear_output(wait=True)
        if resp.get('success'):
            n = resp.get('teams_included', '?')
            display(HTML(f'<span style="color:#22c55e;font-family:Georgia;">'
                         f'&#10003; Round 1 unlocked &#8212; {n} team(s) in leaderboard.</span>'))
        else:
            display(HTML(f'<span style="color:#ef4444;">&#10007; {resp.get("error","unknown")}</span>'))
    _r1u_btn.disabled = False
    _r1u_btn.description = '\\U0001f513  Force Unlock Round 1'

_r1u_btn.on_click(_unlock_r1)
display(widgets.HBox([_r1u_btn, _r1u_out],
        layout=widgets.Layout(margin='0 0 18px 0', align_items='center')))

# ── Analysis ──────────────────────────────────────────────────────────────────
def _r1_analysis():
    resp = get_round_data(1)
    if not resp.get('success') or not resp.get('rows'):
        display(HTML('<p style="color:#94a3b8;font-family:Georgia;">'
                     'No Round 1 data yet.</p>'))
        return

    df = pd.DataFrame(resp['rows'],
                      columns=['team','ts','quarter','chips','prediction','reasoning'])
    df['chips'] = pd.to_numeric(df['chips'], errors='coerce').fillna(0).astype(int)
    n_teams   = df['team'].nunique()
    calls_ord = [ANON_MAP.get(q, q) for q in QUARTERS]

    display(HTML(f'<p style="color:#94a3b8;font-family:Georgia;margin:0 0 10px 0;">'
                 f'{len(df)} row(s) from {n_teams} team(s).</p>'))

    # ── Chart 1: Prediction split per call (horizontal stacked bar) ──────────
    rose_pct, fell_pct = [], []
    for q in QUARTERS:
        sub = df[df['quarter'] == q]
        tot = len(sub)
        rose_pct.append(sub[sub['prediction'] == 'Stock rose'].shape[0] / tot * 100 if tot else 0)
        fell_pct.append(sub[sub['prediction'] == 'Stock fell'].shape[0] / tot * 100 if tot else 0)

    fig = go.Figure()
    fig.add_trace(go.Bar(name='Stock rose ↑', x=rose_pct, y=calls_ord, orientation='h',
                         marker_color='#22c55e',
                         text=[f'{v:.0f}%' for v in rose_pct],
                         textposition='inside', insidetextanchor='middle'))
    fig.add_trace(go.Bar(name='Stock fell ↓', x=fell_pct, y=calls_ord, orientation='h',
                         marker_color='#ef4444',
                         text=[f'{v:.0f}%' for v in fell_pct],
                         textposition='inside', insidetextanchor='middle'))
    for q in QUARTERS:
        actual = ACTUALS[q]
        sym = '↑ actual' if actual == 'positive' else '↓ actual'
        col = '#22c55e' if actual == 'positive' else '#ef4444'
        fig.add_annotation(x=104, y=ANON_MAP.get(q, q), text=sym, showarrow=False,
                           font=dict(color=col, size=11), xanchor='left')
    fig.update_layout(
        barmode='stack', title='Class Prediction Split per Call',
        plot_bgcolor='#0f172a', paper_bgcolor='#1e293b',
        font=dict(color='#e2e8f0', family='Georgia'),
        xaxis=dict(title='% of teams', range=[0, 120]),
        legend=dict(orientation='h', y=1.15), height=310, margin=dict(r=130))
    fig.show()

    # ── Chart 2: Chip allocation heatmap (teams × calls) ─────────────────────
    teams = sorted(df['team'].unique())
    heat  = np.zeros((len(teams), len(QUARTERS)))
    for i, team in enumerate(teams):
        for j, q in enumerate(QUARTERS):
            row = df[(df['team'] == team) & (df['quarter'] == q)]
            if len(row):
                heat[i, j] = row['chips'].values[0]

    fig2 = go.Figure(go.Heatmap(
        z=heat, x=calls_ord, y=teams,
        colorscale=[[0,'#0f172a'],[0.34,'#1e40af'],[0.67,'#7c3aed'],[1,'#f59e0b']],
        zmin=0, zmax=3,
        text=np.where(heat > 0, heat.astype(int).astype(str), '—'),
        texttemplate='%{text}', textfont=dict(size=14),
        colorbar=dict(title='Chips', tickvals=[0,1,2,3], thickness=14)))
    fig2.update_layout(
        title='Chip Allocation — Risk Appetite by Team & Call',
        plot_bgcolor='#0f172a', paper_bgcolor='#1e293b',
        font=dict(color='#e2e8f0'), height=max(260, len(teams) * 40 + 140),
        xaxis=dict(side='top'))
    fig2.show()

    # ── Chart 3: Avg chips & class accuracy side-by-side ─────────────────────
    avg_chips, acc_pct = [], []
    for q in QUARTERS:
        sub    = df[df['quarter'] == q]
        actual = ACTUALS[q]
        avg_chips.append(sub['chips'].mean() if len(sub) else 0)
        correct = (((sub['prediction'] == 'Stock rose') & (actual == 'positive')) |
                   ((sub['prediction'] == 'Stock fell') & (actual == 'negative'))).sum()
        acc_pct.append(correct / len(sub) * 100 if len(sub) else 0)

    fig3 = make_subplots(rows=1, cols=2,
        subplot_titles=('Avg Chips per Call  (higher = class more confident)',
                        'Class Accuracy per Call  (% who called it right)'))
    chip_cols = ['#f59e0b' if c >= 2.5 else '#3b82f6' if c >= 1.5 else '#475569'
                 for c in avg_chips]
    acc_cols  = ['#22c55e' if a >= 60 else '#f59e0b' if a >= 40 else '#ef4444'
                 for a in acc_pct]
    fig3.add_trace(go.Bar(x=calls_ord, y=avg_chips, marker_color=chip_cols,
                          text=[f'{c:.1f}' for c in avg_chips],
                          textposition='outside'), row=1, col=1)
    fig3.add_trace(go.Bar(x=calls_ord, y=acc_pct, marker_color=acc_cols,
                          text=[f'{a:.0f}%' for a in acc_pct],
                          textposition='outside'), row=1, col=2)
    fig3.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='#1e293b',
                       font=dict(color='#e2e8f0', family='Georgia'),
                       showlegend=False, height=350,
                       yaxis=dict(range=[0, 3.9], title='chips'),
                       yaxis2=dict(range=[0, 118], title='%'))
    fig3.show()

    # ── Chart 4: Reasoning keywords ───────────────────────────────────────────
    all_words = []
    for txt in df['reasoning'].dropna():
        words = re.findall(r'\\b[a-z]{3,}\\b', str(txt).lower())
        all_words.extend(w for w in words if w not in STOPWORDS)
    if all_words:
        top = Counter(all_words).most_common(15)
        wds, cnts = zip(*top)
        fig4 = go.Figure(go.Bar(
            x=list(cnts)[::-1], y=list(wds)[::-1], orientation='h',
            marker_color='#818cf8',
            text=list(cnts)[::-1], textposition='outside'))
        fig4.update_layout(
            title='Top Keywords in Reasoning — All Teams, All Calls',
            plot_bgcolor='#0f172a', paper_bgcolor='#1e293b',
            font=dict(color='#e2e8f0'), height=450, margin=dict(l=130))
        fig4.show()

_r1_out = widgets.Output()
_r1_btn = widgets.Button(description='\\u21ba  Fetch & Analyse Round 1',
                          button_style='info', layout=widgets.Layout(width='222px'))

def _run_r1(b=None):
    with _r1_out:
        clear_output(wait=True)
        _r1_analysis()

_r1_btn.on_click(_run_r1)
display(widgets.VBox([_r1_btn, _r1_out]))
_run_r1()
""", "🔵 Round 1 — Predictions"))

# ── Cell 6: Round 2 ───────────────────────────────────────────────────────────
C.append(code("""\
display(HTML(
    '<div class="inst-hdr"><h2>Round 2 &#8212; Signal Classification</h2>'
    '<p>After viewing infographics, teams classify each call&#8217;s signals as '
    'Consistent, Divergent, or Unclear. Did the images help or confuse?</p></div>'))

# ── Force Unlock ──────────────────────────────────────────────────────────────
_r2u_out = widgets.Output()
_r2u_btn = widgets.Button(description='\\U0001f513  Force Unlock Round 2',
                           button_style='danger',
                           layout=widgets.Layout(width='222px', height='38px'))

def _unlock_r2(b):
    _r2u_btn.disabled = True
    _r2u_btn.description = '\\u23f3  Unlocking...'
    resp = do_force_unlock(2)
    with _r2u_out:
        clear_output(wait=True)
        if resp.get('success'):
            n = resp.get('teams_included', '?')
            display(HTML(f'<span style="color:#22c55e;font-family:Georgia;">'
                         f'&#10003; Round 2 unlocked &#8212; {n} team(s) in leaderboard.</span>'))
        else:
            display(HTML(f'<span style="color:#ef4444;">&#10007; {resp.get("error","unknown")}</span>'))
    _r2u_btn.disabled = False
    _r2u_btn.description = '\\U0001f513  Force Unlock Round 2'

_r2u_btn.on_click(_unlock_r2)
display(widgets.HBox([_r2u_btn, _r2u_out],
        layout=widgets.Layout(margin='0 0 18px 0', align_items='center')))

# ── Analysis ──────────────────────────────────────────────────────────────────
def _r2_analysis():
    resp = get_round_data(2)
    if not resp.get('success') or not resp.get('rows'):
        display(HTML('<p style="color:#94a3b8;font-family:Georgia;">No Round 2 data yet.</p>'))
        return

    # [team, ts, quarter, classification]
    df = pd.DataFrame(resp['rows'], columns=['team','ts','quarter','classification'])
    calls_ord = [ANON_MAP.get(q, q) for q in QUARTERS]

    def _cls(s):
        s = str(s)
        if s.startswith('A'): return 'A — Consistent'
        if s.startswith('B'): return 'B — Divergent'
        if s.startswith('C'): return 'C — Unclear'
        return s

    df['cls'] = df['classification'].apply(_cls)
    n_teams = df['team'].nunique()
    display(HTML(f'<p style="color:#94a3b8;font-family:Georgia;margin:0 0 10px 0;">'
                 f'{len(df)} row(s) from {n_teams} team(s).</p>'))

    # ── Chart 1: Classification distribution per call ─────────────────────────
    cls_labels = ['A — Consistent', 'B — Divergent', 'C — Unclear']
    cls_colors = ['#22c55e', '#f59e0b', '#64748b']
    fig = go.Figure()
    for lbl, col in zip(cls_labels, cls_colors):
        counts = [df[(df['quarter'] == q) & (df['cls'] == lbl)].shape[0]
                  for q in QUARTERS]
        fig.add_trace(go.Bar(name=lbl, x=calls_ord, y=counts,
                             marker_color=col,
                             text=counts, textposition='outside'))
    fig.update_layout(
        barmode='group',
        title='Signal Classification — How the Class Read Each Call',
        plot_bgcolor='#0f172a', paper_bgcolor='#1e293b',
        font=dict(color='#e2e8f0', family='Georgia'),
        legend=dict(orientation='h', y=1.15), height=370,
        yaxis=dict(title='No. of teams', dtick=1))
    fig.show()

    # ── Chart 2: Consensus strength heatmap ──────────────────────────────────
    heat_z, heat_txt = [], []
    for lbl in cls_labels:
        row_z, row_t = [], []
        for q in QUARTERS:
            sub = df[df['quarter'] == q]
            pct = sub[sub['cls'] == lbl].shape[0] / len(sub) * 100 if len(sub) else 0
            row_z.append(pct)
            row_t.append(f'{pct:.0f}%')
        heat_z.append(row_z)
        heat_txt.append(row_t)

    fig2 = go.Figure(go.Heatmap(
        z=heat_z, x=calls_ord,
        y=['A Consistent', 'B Divergent', 'C Unclear'],
        colorscale=[[0,'#0f172a'],[0.5,'#1e40af'],[1,'#f59e0b']],
        zmin=0, zmax=100,
        text=heat_txt, texttemplate='%{text}', textfont=dict(size=13),
        colorbar=dict(title='% teams', ticksuffix='%', thickness=14)))
    fig2.update_layout(
        title='Consensus Heatmap — % of Teams Choosing Each Classification',
        plot_bgcolor='#0f172a', paper_bgcolor='#1e293b',
        font=dict(color='#e2e8f0'), height=280)
    fig2.show()

    # ── Summary table ────────────────────────────────────────────────────────
    rows_html = ''
    for q in QUARTERS:
        sub = df[df['quarter'] == q]
        if not len(sub):
            continue
        top_cls  = sub['cls'].value_counts().index[0]
        pct_top  = sub['cls'].value_counts().values[0] / len(sub) * 100
        strength = ('&#x1F7E2; Strong' if pct_top >= 70
                    else '&#x1F7E1; Moderate' if pct_top >= 50
                    else '&#x1F534; Split')
        rows_html += (f'<tr><td style="color:#818cf8;">{ANON_MAP.get(q,q)}</td>'
                      f'<td>{top_cls}</td><td>{pct_top:.0f}%</td>'
                      f'<td>{strength}</td></tr>')
    display(HTML(
        '<h4 style="color:#94a3b8;font-family:Georgia;margin:16px 0 4px 0;">'
        'Class Consensus Summary</h4>'
        '<table class="ag-table"><tr>'
        '<th>Call</th><th>Majority classification</th>'
        '<th>% agreement</th><th>Consensus strength</th></tr>'
        + rows_html + '</table>'))

_r2_out = widgets.Output()
_r2_btn = widgets.Button(description='\\u21ba  Fetch & Analyse Round 2',
                          button_style='info', layout=widgets.Layout(width='222px'))

def _run_r2(b=None):
    with _r2_out:
        clear_output(wait=True)
        _r2_analysis()

_r2_btn.on_click(_run_r2)
display(widgets.VBox([_r2_btn, _r2_out]))
_run_r2()
""", "🟡 Round 2 — Signal Classification"))

# ── Cell 7: Round 3 ───────────────────────────────────────────────────────────
C.append(code("""\
display(HTML(
    '<div class="inst-hdr"><h2>Round 3 &#8212; Final Predictions</h2>'
    '<p>Teams revise their Round 1 predictions after seeing the infographic signals. '
    'Key question: did the visual evidence change minds?</p></div>'))

# ── Force Unlock ──────────────────────────────────────────────────────────────
_r3u_out = widgets.Output()
_r3u_btn = widgets.Button(description='\\U0001f513  Force Unlock Round 3',
                           button_style='danger',
                           layout=widgets.Layout(width='222px', height='38px'))

def _unlock_r3(b):
    _r3u_btn.disabled = True
    _r3u_btn.description = '\\u23f3  Unlocking...'
    resp = do_force_unlock(3)
    with _r3u_out:
        clear_output(wait=True)
        if resp.get('success'):
            n = resp.get('teams_included', '?')
            display(HTML(f'<span style="color:#22c55e;font-family:Georgia;">'
                         f'&#10003; Round 3 unlocked &#8212; {n} team(s) in leaderboard.</span>'))
        else:
            display(HTML(f'<span style="color:#ef4444;">&#10007; {resp.get("error","unknown")}</span>'))
    _r3u_btn.disabled = False
    _r3u_btn.description = '\\U0001f513  Force Unlock Round 3'

_r3u_btn.on_click(_unlock_r3)
display(widgets.HBox([_r3u_btn, _r3u_out],
        layout=widgets.Layout(margin='0 0 18px 0', align_items='center')))

# ── Analysis ──────────────────────────────────────────────────────────────────
def _r3_analysis():
    cols = ['team','ts','quarter','chips','prediction','reasoning']
    r1 = get_round_data(1)
    r3 = get_round_data(3)

    if not r1.get('success') or not r1.get('rows'):
        display(HTML('<p style="color:#94a3b8;font-family:Georgia;">No Round 1 data.</p>'))
        return
    if not r3.get('success') or not r3.get('rows'):
        display(HTML('<p style="color:#94a3b8;font-family:Georgia;">No Round 3 data yet.</p>'))
        return

    df1 = pd.DataFrame(r1['rows'], columns=cols)
    df3 = pd.DataFrame(r3['rows'], columns=cols)
    df1['chips'] = pd.to_numeric(df1['chips'], errors='coerce').fillna(0).astype(int)
    df3['chips'] = pd.to_numeric(df3['chips'], errors='coerce').fillna(0).astype(int)

    calls_ord = [ANON_MAP.get(q, q) for q in QUARTERS]
    teams     = sorted(set(df1['team'].unique()) | set(df3['team'].unique()))

    # ── Chart 1: Who changed their prediction? ────────────────────────────────
    changed_by_call = {q: 0 for q in QUARTERS}
    same_by_call    = {q: 0 for q in QUARTERS}
    changed_teams   = []
    flip_rows = []

    for team in teams:
        team_flipped = False
        for q in QUARTERS:
            r1_row = df1[(df1['team'] == team) & (df1['quarter'] == q)]
            r3_row = df3[(df3['team'] == team) & (df3['quarter'] == q)]
            if len(r1_row) and len(r3_row):
                p1, p3 = r1_row['prediction'].values[0], r3_row['prediction'].values[0]
                if p1 != p3:
                    changed_by_call[q] += 1
                    if not team_flipped:
                        changed_teams.append(team)
                        team_flipped = True
                    flip_rows.append({'team': team, 'call': ANON_MAP.get(q,q),
                                      'r1': p1, 'r3': p3})
                else:
                    same_by_call[q] += 1

    fig = go.Figure()
    fig.add_trace(go.Bar(name='Changed prediction', x=calls_ord,
                         y=[changed_by_call[q] for q in QUARTERS],
                         marker_color='#f59e0b',
                         text=[changed_by_call[q] for q in QUARTERS],
                         textposition='outside'))
    fig.add_trace(go.Bar(name='Kept prediction', x=calls_ord,
                         y=[same_by_call[q] for q in QUARTERS],
                         marker_color='#3b82f6',
                         text=[same_by_call[q] for q in QUARTERS],
                         textposition='outside'))
    fig.update_layout(
        barmode='stack',
        title='Did Round 2 Change Minds? — Prediction Flips per Call',
        plot_bgcolor='#0f172a', paper_bgcolor='#1e293b',
        font=dict(color='#e2e8f0', family='Georgia'),
        legend=dict(orientation='h', y=1.15), height=360,
        yaxis=dict(title='No. of teams', dtick=1))
    fig.show()

    if flip_rows:
        flip_df = pd.DataFrame(flip_rows)
        rows_html = ''.join(
            f'<tr><td>{r["team"]}</td><td>{r["call"]}</td>'
            f'<td style="color:#ef4444;">{r["r1"]}</td>'
            f'<td style="color:#22c55e;">{r["r3"]}</td></tr>'
            for _, r in flip_df.iterrows())
        display(HTML(
            '<h4 style="color:#94a3b8;font-family:Georgia;margin:14px 0 4px 0;">'
            'All Prediction Changes</h4>'
            '<table class="ag-table" style="max-width:560px;"><tr>'
            '<th>Team</th><th>Call</th><th>Round 1</th><th>Round 3</th></tr>'
            + rows_html + '</table>'))

    # ── Chart 2: Chip changes R1 → R3 ────────────────────────────────────────
    avg_delta = []
    for q in QUARTERS:
        deltas = []
        for team in teams:
            r1_row = df1[(df1['team'] == team) & (df1['quarter'] == q)]
            r3_row = df3[(df3['team'] == team) & (df3['quarter'] == q)]
            if len(r1_row) and len(r3_row):
                deltas.append(int(r3_row['chips'].values[0]) - int(r1_row['chips'].values[0]))
        avg_delta.append(np.mean(deltas) if deltas else 0)

    delta_cols = ['#22c55e' if d > 0 else '#ef4444' if d < 0 else '#475569'
                  for d in avg_delta]
    fig2 = go.Figure(go.Bar(x=calls_ord, y=avg_delta, marker_color=delta_cols,
                            text=[f'{d:+.1f}' for d in avg_delta],
                            textposition='outside'))
    fig2.add_hline(y=0, line_color='#475569', line_width=1)
    fig2.update_layout(
        title='Avg Chip Shift R1 → R3  (+ = class grew more confident after seeing signals)',
        plot_bgcolor='#0f172a', paper_bgcolor='#1e293b',
        font=dict(color='#e2e8f0', family='Georgia'), height=320,
        yaxis=dict(title='Avg chip delta', range=[-2.5, 2.5]))
    fig2.show()

    # ── Chart 3: R1 vs R3 prediction split comparison ─────────────────────────
    rose_r1, rose_r3 = [], []
    for q in QUARTERS:
        s1 = df1[df1['quarter'] == q]
        s3 = df3[df3['quarter'] == q]
        rose_r1.append(s1[s1['prediction'] == 'Stock rose'].shape[0] / len(s1) * 100 if len(s1) else 0)
        rose_r3.append(s3[s3['prediction'] == 'Stock rose'].shape[0] / len(s3) * 100 if len(s3) else 0)

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=calls_ord, y=rose_r1, name='Round 1',
                              mode='lines+markers',
                              marker=dict(size=10), line=dict(color='#3b82f6', width=2)))
    fig3.add_trace(go.Scatter(x=calls_ord, y=rose_r3, name='Round 3',
                              mode='lines+markers',
                              marker=dict(size=10), line=dict(color='#f59e0b', width=2, dash='dash')))
    for i, q in enumerate(QUARTERS):
        actual = ACTUALS[q]
        col = '#22c55e' if actual == 'positive' else '#ef4444'
        fig3.add_hline(y=50, line_dash='dot', line_color='#334155')
        fig3.add_annotation(x=calls_ord[i], y=rose_r3[i] + 5,
                            text='↑' if actual == 'positive' else '↓',
                            font=dict(color=col, size=14), showarrow=False)
    fig3.update_layout(
        title='% Predicting "Stock Rose" — Round 1 vs Round 3',
        plot_bgcolor='#0f172a', paper_bgcolor='#1e293b',
        font=dict(color='#e2e8f0', family='Georgia'),
        legend=dict(orientation='h', y=1.12), height=360,
        yaxis=dict(title='% predicting ↑', range=[0, 110]))
    fig3.show()

_r3_out = widgets.Output()
_r3_btn = widgets.Button(description='\\u21ba  Fetch & Analyse Round 3',
                          button_style='info', layout=widgets.Layout(width='222px'))

def _run_r3(b=None):
    with _r3_out:
        clear_output(wait=True)
        _r3_analysis()

_r3_btn.on_click(_run_r3)
display(widgets.VBox([_r3_btn, _r3_out]))
_run_r3()
""", "🟢 Round 3 — Final Predictions"))

# ── Cell 8: Leaderboard & podium ──────────────────────────────────────────────
C.append(code("""\
display(HTML(
    '<div class="inst-hdr"><h2>&#x1F3C6; Final Leaderboard &amp; Podium</h2>'
    '<p>Scores = chips staked &#215; outcome (+chips if correct, &#8722;chips if wrong). '
    'Uses Round 3 predictions; falls back to Round 1 per team.</p></div>'))

def _score_team(team, df):
    score, details = 0, []
    for q in QUARTERS:
        row = df[(df['team'] == team) & (df['quarter'] == q)]
        if not len(row):
            details.append({'call': ANON_MAP.get(q,q), 'pred': '—',
                            'actual': ACTUALS[q], 'chips': 0, 'pts': 0, 'ok': False})
            continue
        pred   = row['prediction'].values[0]
        chips  = int(row['chips'].values[0])
        actual = ACTUALS[q]
        ok     = ((pred == 'Stock rose') and (actual == 'positive')) or \\
                 ((pred == 'Stock fell') and (actual == 'negative'))
        pts    = chips if ok else -chips
        score += pts
        details.append({'call': ANON_MAP.get(q,q), 'pred': pred,
                        'actual': actual, 'chips': chips, 'pts': pts, 'ok': ok})
    return score, details

def _draw_podium(lb):
    while len(lb) < 3:
        lb.append({'team': '—', 'score': 0})

    # Podium arrangement: 2nd left, 1st centre, 3rd right
    order    = [1, 0, 2]
    heights  = [0.58, 1.00, 0.38]
    colors   = ['#94a3b8', '#f59e0b', '#92400e']
    medals   = ['\\U0001f948', '\\U0001f947', '\\U0001f949']
    rank_lbl = ['2nd', '1st', '3rd']
    positions = [0.21, 0.50, 0.79]
    bar_w     = 0.23

    fig, ax = plt.subplots(figsize=(11, 6))
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.75)
    ax.axis('off')

    for i, (pos, h, col, medal, rlbl) in enumerate(
            zip(positions, heights, colors, medals, rank_lbl)):
        entry = lb[order[i]]
        team  = str(entry['team'])
        scr   = entry['score']

        # Podium block
        rect = plt.Rectangle((pos - bar_w / 2, 0.04), bar_w, h,
                              facecolor=col, alpha=0.88, zorder=2)
        ax.add_patch(rect)

        # Rank inside block
        ax.text(pos, 0.04 + h / 2, rlbl, ha='center', va='center',
                fontsize=18, fontweight='bold', color='#0f172a', zorder=3)

        # Medal emoji above block
        ax.text(pos, 0.04 + h + 0.07, medal, ha='center', va='bottom',
                fontsize=24, zorder=3)

        # Team name
        ax.text(pos, 0.04 + h + 0.20, team, ha='center', va='bottom',
                fontsize=12, fontweight='bold', color='#e2e8f0', zorder=3)

        # Score
        score_str = ('+' if scr > 0 else '') + str(scr) + ' pts'
        ax.text(pos, 0.04 + h + 0.30, score_str, ha='center', va='bottom',
                fontsize=11, color=col, zorder=3)

    ax.text(0.5, 1.70, 'Workshop Leaderboard', ha='center', va='top',
            fontsize=18, fontweight='bold', color='#f59e0b', fontfamily='Georgia')
    plt.tight_layout(pad=0)
    plt.show()
    plt.close()

def _build_leaderboard():
    cols = ['team','ts','quarter','chips','prediction','reasoning']
    r3 = get_round_data(3)
    r1 = get_round_data(1)
    df3 = pd.DataFrame(r3['rows'], columns=cols) if r3.get('rows') else pd.DataFrame(columns=cols)
    df1 = pd.DataFrame(r1['rows'], columns=cols) if r1.get('rows') else pd.DataFrame(columns=cols)

    if df3.empty and df1.empty:
        display(HTML('<p style="color:#94a3b8;font-family:Georgia;">No data yet.</p>'))
        return

    for df in [df3, df1]:
        if not df.empty:
            df['chips'] = pd.to_numeric(df['chips'], errors='coerce').fillna(0).astype(int)

    all_teams = sorted(set(
        (list(df3['team'].unique()) if not df3.empty else []) +
        (list(df1['team'].unique()) if not df1.empty else [])))

    lb, all_details = [], {}
    for team in all_teams:
        t3 = df3[df3['team'] == team] if not df3.empty else pd.DataFrame()
        t1 = df1[df1['team'] == team] if not df1.empty else pd.DataFrame()
        df_final = t3 if len(t3) else t1
        score, details = _score_team(team, df_final)
        lb.append({'team': team, 'score': score})
        all_details[team] = details

    lb.sort(key=lambda x: x['score'], reverse=True)

    # ── Podium ────────────────────────────────────────────────────────────────
    _draw_podium(lb[:])

    # ── Full standings table ──────────────────────────────────────────────────
    rows_html = ''
    for rank, entry in enumerate(lb, 1):
        team  = entry['team']
        score = entry['score']
        col   = '#22c55e' if score > 0 else '#ef4444' if score < 0 else '#94a3b8'
        medal = ('&#x1F947;' if rank == 1 else '&#x1F948;' if rank == 2
                 else '&#x1F949;' if rank == 3 else f'#{rank}')
        rows_html += (f'<tr><td style="text-align:center;">{medal}</td>'
                      f'<td style="font-weight:bold;">{team}</td>'
                      f'<td style="color:{col};font-weight:bold;">'
                      f'{"+" if score > 0 else ""}{score}</td></tr>')
    display(HTML(
        '<h4 style="color:#94a3b8;font-family:Georgia;margin:22px 0 6px 0;">'
        'Full Standings</h4>'
        '<table class="ag-table" style="max-width:380px;">'
        '<tr><th>#</th><th>Team</th><th>Score</th></tr>'
        + rows_html + '</table>'))

    # ── Accuracy matrix (teams × calls) ───────────────────────────────────────
    teams_m  = [e['team'] for e in lb]
    calls_ord = [ANON_MAP.get(q, q) for q in QUARTERS]
    mat_z, mat_t = [], []
    for team in teams_m:
        rz, rt = [], []
        for d in all_details.get(team, []):
            if d['pred'] == '—':
                rz.append(0);  rt.append('—')
            elif d['ok']:
                rz.append(1);  rt.append(f'\\u2713 +{d["chips"]}')
            else:
                rz.append(-1); rt.append(f'\\u2717 \\u2212{d["chips"]}')
        mat_z.append(rz)
        mat_t.append(rt)

    fig_m = go.Figure(go.Heatmap(
        z=mat_z, x=calls_ord, y=teams_m,
        colorscale=[[0,'#450a0a'],[0.5,'#1e293b'],[1,'#14532d']],
        zmin=-1, zmax=1,
        text=mat_t, texttemplate='%{text}', textfont=dict(size=13),
        showscale=False))
    fig_m.update_layout(
        title='Accuracy Matrix — Who Got Which Calls Right',
        plot_bgcolor='#0f172a', paper_bgcolor='#1e293b',
        font=dict(color='#e2e8f0', family='Georgia'),
        height=max(280, len(teams_m) * 42 + 150),
        xaxis=dict(side='top'))
    fig_m.show()

    # ── Score distribution ────────────────────────────────────────────────────
    scores = [e['score'] for e in lb]
    if len(scores) >= 2:
        fig_d = go.Figure(go.Histogram(
            x=scores, nbinsx=max(4, len(scores)),
            marker_color='#818cf8',
            marker_line_color='#334155', marker_line_width=1.5))
        fig_d.add_vline(x=np.mean(scores), line_dash='dash', line_color='#f59e0b',
                        annotation_text=f'Mean: {np.mean(scores):.1f}',
                        annotation_font_color='#f59e0b',
                        annotation_position='top right')
        fig_d.update_layout(
            title='Score Distribution Across Teams',
            plot_bgcolor='#0f172a', paper_bgcolor='#1e293b',
            font=dict(color='#e2e8f0', family='Georgia'), height=300,
            xaxis_title='Score (pts)', yaxis_title='No. of teams')
        fig_d.show()

_lb_out = widgets.Output()
_lb_btn = widgets.Button(description='\\u21ba  Fetch & Render Leaderboard',
                          button_style='info', layout=widgets.Layout(width='240px'))

def _run_lb(b=None):
    with _lb_out:
        clear_output(wait=True)
        _build_leaderboard()

_lb_btn.on_click(_run_lb)
display(widgets.VBox([_lb_btn, _lb_out]))
_run_lb()
""", "🏆 Final Leaderboard & Podium"))

# ── Cell 9: Reflections ───────────────────────────────────────────────────────
C.append(code("""\
display(HTML(
    '<div class="inst-hdr"><h2>&#x1F4AC; Class Reflections</h2>'
    '<p>Personal reflections submitted after the reveal. '
    'Use these to anchor the debrief discussion.</p></div>'))

def _show_reflections():
    resp = get_reflections()
    if not resp.get('success') or not resp.get('rows'):
        display(HTML('<p style="color:#94a3b8;font-family:Georgia;">'
                     'No reflections submitted yet.</p>'))
        return

    # [team, ts, q1, q2, q3]
    df = pd.DataFrame(resp['rows'], columns=['team','ts','q1','q2','q3'])
    display(HTML(f'<p style="color:#94a3b8;font-family:Georgia;">'
                 f'{len(df)} reflection(s) received.</p>'))

    q_labels = ['What surprised you most about the actual outcomes?',
                'Which signal (text / audio / images) did you find most useful, and why?',
                'What would you do differently if you ran this analysis on a real investment decision?']

    for _, row in df.iterrows():
        qs_html = ''
        for qi, (col, lbl) in enumerate(zip(['q1','q2','q3'], q_labels), 1):
            val = str(row.get(col, '')).strip() or '<em style="color:#475569;">No response</em>'
            qs_html += (f'<div style="margin-bottom:10px;">'
                        f'<div style="color:#f59e0b;font-size:0.8em;margin-bottom:3px;">'
                        f'Q{qi} — {lbl}</div>'
                        f'<div style="color:#e2e8f0;">{val}</div></div>')
        display(HTML(
            f'<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;'
            f'padding:14px 18px;margin:8px 0;font-family:Georgia,serif;">'
            f'<div style="color:#818cf8;font-weight:bold;font-size:1.05em;'
            f'margin-bottom:12px;">{row["team"]}</div>'
            f'{qs_html}</div>'))

_ref_out = widgets.Output()
_ref_btn = widgets.Button(description='\\u21ba  Fetch Reflections',
                           button_style='info', layout=widgets.Layout(width='185px'))

def _run_ref(b=None):
    with _ref_out:
        clear_output(wait=True)
        _show_reflections()

_ref_btn.on_click(_run_ref)
display(widgets.VBox([_ref_btn, _ref_out]))
_run_ref()
""", "💬 Reflections"))

# ── Build notebook JSON ────────────────────────────────────────────────────────
NB = {
    'nbformat': 4,
    'nbformat_minor': 5,
    'metadata': {
        'colab': {'provenance': []},
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python', 'version': '3.10.0'}
    },
    'cells': C
}

out_path = '/tmp/AG952/week10/AG952_Week10_Instructor.ipynb'
with open(out_path, 'w') as f:
    json.dump(NB, f, indent=1)

print(f'Written {len(C)} cells → {out_path}')
