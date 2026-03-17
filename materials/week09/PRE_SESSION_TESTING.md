# AG952 Workshop 9 — Pre-Session Testing Checklist

Run these tests the day before the session on a fresh Colab runtime.

## 1. Data access

- [ ] Open the student notebook via the Colab badge link
- [ ] Run Step 0 (dependencies install, including numpy<2.0 pin and captum, ~90 seconds)
- [ ] Confirm the numpy version check passes without triggering the restart prompt
- [ ] Run CP0 — select any team name, confirm registration message
- [ ] Run CP1 — confirm the CSV loads from the DATA_URL, all four panels render (articles per year, newspapers, word count distribution, mean length by era), and the summary table prints
- [ ] If the URL fetch fails: check the GitHub repo has the CSV committed at `materials/week09/data/brewdog_articles_factiva.csv`

## 2. Part 1 — Topic modelling (CP2 and CP3)

- [ ] CP2: run with default settings, confirm word cloud and token histogram appear
- [ ] CP3: run LDA with k=6, confirm era-breakdown charts and top-word panels render for all three eras

## 3. Part 2 — Sentiment analysis (CP4)

- [ ] CP4 "Run analysis" button: select "FinBERT" with sample 60, confirm LM and VADER scores compute for all articles and FinBERT inference runs on the sample (~3 min on CPU)
- [ ] CP4 "Sentiment over time": confirm multi-method trajectory chart renders with era shading
- [ ] CP4 "By newspaper": confirm horizontal bar chart and source-type trajectory render
- [ ] CP4 "By theme": confirm 2x2 theme subplot grid renders
- [ ] CP4 "Save responses": confirm session_data is updated and the earliest-signal reflection dropdown is enabled

## 4. Part 3 — Explainability (CP5)

- [ ] CP5 Button A (Load FinBERT): confirm model downloads (~420 MB first run) and prediction table for all 5 sentences prints
- [ ] CP5 Button B (Explain with IG): confirm transformers_interpret runs and HTML attribution visualisations display for all 5 sentences (may be slow on CPU, ~2 min)
- [ ] CP5 Button C (Attribution bar charts): confirm bar charts render for sentences 3 and 4 with green/red colouring
- [ ] Confirm the CP5 reflection dropdown is enabled after Button B

## 5. Part 4 — Submission (CP6)

- [ ] CP6: type a test note (at least 20 words), confirm word counter updates correctly
- [ ] Submit: confirm POST returns success or prints session data if APPS_SCRIPT_URL is not set

## 6. Submission

- [ ] Submit a test response from a team name not used in real session (e.g. "TEST TEAM")
- [ ] Confirm row appears in Google Sheet with all fields populated
- [ ] Delete the test row from the sheet before the session

## 7. Timing check

Run the full notebook end-to-end on Colab CPU and note actual timings:

| Section | Expected | Actual |
|---------|----------|--------|
| Step 0 (installs including captum) | ~90s | |
| CP0--CP1 | ~30s | |
| CP2--CP3 | ~3 min | |
| CP4 (Run analysis -- FinBERT, 60 articles) | ~3 min | |
| CP4 (exploration buttons) | ~30s | |
| CP5 Button A (load FinBERT) | ~30s (cached) | |
| CP5 Button B (IG explanations, 5 sentences) | ~2 min | |
| CP5 Button C (bar charts) | ~10s | |
| CP6 (submission) | -- | |

**Total target: 45 minutes on CPU.** If CP4 FinBERT inference is too slow, switch the sample to 40 articles or use the "Dictionary only" option for the demo; FinBERT can still be run after CP3 while students are reading the feedback cell.

## 8. Colab GPU recommendation

If your institution has Colab Pro access, set the runtime to T4 GPU before the session.
Transformer inference is 10--15 times faster on GPU; this reduces CP4 and CP5 combined from ~6 minutes to under 1 minute.
No code changes are required -- HuggingFace pipelines detect GPU automatically.
captum integrated gradients also runs substantially faster on GPU.
