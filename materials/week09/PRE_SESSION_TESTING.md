# AG952 Workshop 9 — Pre-Session Testing Checklist

Run these tests the day before the session on a fresh Colab runtime.

## 1. Data access

- [ ] Open the student notebook via the Colab badge link
- [ ] Run Step 0 (dependencies install, ~60 seconds)
- [ ] Run CP0 — select any team name, confirm registration message
- [ ] Run CP1 — confirm the CSV loads from the DATA_URL and the two charts render
- [ ] If the URL fetch fails: check the GitHub repo has the CSV committed at `materials/week09/data/brewdog_articles_factiva.csv`

## 2. Part 1 (traditional NLP)

- [ ] CP2: run with default settings, confirm word cloud and token histogram appear
- [ ] CP3: run LDA with k=6, confirm top-words print and stacked area chart renders
- [ ] CP4: run "All three (comparison mode)", confirm all three score columns computed and trajectory chart renders

## 3. Part 2 (transformers)

- [ ] CP5 Button A (tokenisation): confirm FinBERT tokeniser downloads and tokenisation demo prints
- [ ] CP5 Button B (context sensitivity): confirm Markdown panel renders
- [ ] CP5 Button C (attention): confirm attention heatmap renders (may fail on CPU — that is acceptable, the cell prints a graceful message)
- [ ] CP6 — DistilBERT option (faster, ~2 min on CPU): confirm inference runs on 40-article sample and VADER agreement rate is reported
- [ ] CP6 — FinBERT option (slower, ~4 min on CPU): confirm inference runs and disagreement articles are listed
- [ ] CP7: confirm VADER vs transformer comparison runs, trajectory chart and method-agreement heatmap render
- [ ] CP8: type a test note, confirm word counter updates, confirm submission POST (if Apps Script deployed)

## 4. Submission

- [ ] Submit a test response from a team name not used in real session (e.g. "TEST TEAM")
- [ ] Confirm row appears in Google Sheet
- [ ] Delete the test row from the sheet before the session

## 5. Timing check

Run the full notebook end-to-end on Colab CPU and note actual timings:

| Section | Expected | Actual |
|---------|----------|--------|
| Step 0 (installs) | ~60s | |
| CP0–CP1 | ~30s | |
| CP2–CP4 | ~3 min | |
| CP5 (tokeniser download + walkthrough) | ~2–4 min | |
| CP6 (DistilBERT, 40 articles) | ~2 min | |
| CP6 (FinBERT, 40 articles) | ~4 min | |
| CP7 | ~30s | |
| CP8 | — | |

**Total target: ≤ 55 minutes on CPU.** Default sample size is already set to 40 articles in CP6. Increase to 80–120 if time permits.

## 6. Colab GPU recommendation

If your institution has Colab Pro access, set the runtime to T4 GPU before the session.
Transformer inference is 10–15× faster on GPU; this reduces CP5–CP7 from ~8 minutes to under 1 minute.
No code changes are required — HuggingFace pipelines detect GPU automatically.
