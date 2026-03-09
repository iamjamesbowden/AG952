# AG952 Assignment – Getting Started Guide

**Module:** AG952 Textual Analytics for Accounting and Finance
**Assignment:** Computational Text Analysis Project
**Deadline:** 1 April 2026

---

## 1. What This Assignment Is

You will use a Google Colab notebook to run a computational text analysis pipeline on a corpus of US corporate filings. The notebook walks you through every stage: loading data, making pre-processing decisions, running sentiment analysis, applying a secondary metric, and generating outputs for your written report.

You are automatically assigned to one of four research scenarios based on your student number. Each scenario uses a different corpus of 10-K filings focused on a particular theme:

- **Scenario A** – Climate and ESG Risk Language in the US Energy Sector (2019–2023), 138 filings, 30 firms
- **Scenario B** – Narrative Predictors of Corporate Financial Distress (2015–2023), 175 filings, 38 firms
- **Scenario C** – Risk Disclosure and the 2023 US Regional Banking Crisis, 159 filings, 37 banks
- **Scenario D** – Supply Chain Risk Disclosure Before and After COVID-19 (2019–2023), 175 filings, 38 firms

Your scenario is fixed once you enter your student number. It cannot be changed.

---

## 2. Before You Start

**Make a copy of the notebook.** The first time you open it, go to File > Save a copy in Drive (or File > Save a copy in GitHub if you prefer). Work from your own copy — do not edit the shared original.

**Note the deadline.** Submission closes at 1 April 2026. Colab sessions time out after roughly 90 minutes of inactivity, so plan to work in focused sittings rather than leaving the tab idle.

**What you will submit:**
- A written report (PDF) containing all required outputs and your written discussion
- A completed manual validation CSV (downloaded from the notebook)
- Any supplementary files as specified — all uploaded to Moodle

---

## 3. Every Session: Run Step 0 First

Each time you open the notebook in a new Colab session, the runtime environment is completely fresh. Nothing from your previous session is retained in memory.

**You must run Step 0 at the start of every single session.** Step 0 clones the AG952 GitHub repository and sets up the files the notebook depends on. If you skip it, every subsequent step will fail.

To run a cell, click on it and press **Shift + Enter**, or click the play button to the left of the cell.

Run Step 0, wait for it to finish (you will see a confirmation message), then continue from wherever you left off.

---

## 4. Step-by-Step Guide

Work through the steps in order. Do not skip steps or run them out of sequence.

### Step 1 – Install and Import Dependencies

Run this cell and wait. It installs the required Python packages and imports everything the notebook needs. This can take 30–60 seconds. You will see a progress indicator. Once it finishes, continue.

Nothing is required from you here.

### Step 2 – Enter Your Student Number

Run the cell. An input box will appear **at the bottom of the cell's output area** — scroll down if you cannot see it. Type your student number exactly and press Enter.

The notebook will tell you which scenario (A, B, C, or D) you have been assigned to. Make a note of this. Your scenario determines your corpus.

**Gotcha:** If you run Step 2 a second time in the same session (e.g. after re-running Step 1), you will be re-assigned. Your scenario should not change since it is based on your student number, but avoid running Step 2 more than once per session unless necessary.

### Step 3 – Load the Corpus

Run this cell. Your assigned corpus will be loaded and a dropdown will appear. Each filing contains two sections:

- **item_1a** – Risk Factors
- **item_7** – Management Discussion and Analysis (MD&A)

Use the dropdown to select which section(s) you will analyse:

- **Both sections combined (full narrative)** – the two sections are merged into a single text per firm-year, treating the complete narrative disclosure as the unit of analysis.
- **item_1a — Risk Factors only** – only the Risk Factors section is retained.
- **item_7 — MD&A only** – only the MD&A section is retained.

This is your first methodological decision and you must justify it in your written report with reference to relevant literature and your scenario's research question. The working corpus updates automatically when you change the dropdown. Your selection is recorded and submitted with your other choices in Step 12.

### Step 4 – Record Pre-Processing Decisions

Run the cell to display five dropdown menus. Set each one according to your chosen approach:

1. **Case folding** – Choose Yes (lowercase all tokens) or No (preserve original case). Lowercasing means "Risk" and "risk" are treated as the same token; preserving case retains the distinction between proper nouns and common words. This choice affects dictionary matching, topic model vocabulary, and downstream analysis.

2. **Stop-word list** – Choose between Standard NLTK (removes common English words) or Finance-adjusted (also removes common words but retains modal verbs such as "may", "could", "will" and negation terms such as "not", "no"). The finance-adjusted list is often preferable for sentiment analysis of financial text.

3. **Normalisation** – Choose Lemmatisation (reduces words to their dictionary form), Stemming (cruder reduction to a root form), or None (keep words as they appear). Lemmatisation is generally preferred for interpretability.

4. **Number handling** – Choose Remove (delete all numeric tokens), Retain (keep them), or Replace with placeholder (swap all numbers for a generic token like NUM). Consider whether numbers carry meaning in your context.

5. **TF-IDF weighting** – Choose Yes or No. TF-IDF downweights terms that appear frequently across all documents. Relevant if you are using a model that relies on term frequency.

Your choices are shown live in a confirmation panel below the dropdowns. Check this panel before moving on. You will need to report and justify all five choices.

### Step 5 – Apply Pre-Processing

Run the cell. The pre-processing pipeline runs automatically using the choices you made in Step 4. The cell will print the first 30 tokens of a sample document so you can sanity-check the output.

Check that the tokens look sensible for your choices. If something looks wrong (e.g. numbers are still present when you chose Remove), go back to Step 4 and check your settings, then re-run Step 5.

### Step 6 – Select Sentiment Model and Set Thresholds

Run the cell. Three inputs appear:

1. **Sentiment model dropdown** – Choose one of:
   - **lm_dictionary** – Loughran-McDonald financial sentiment dictionary
   - **harvard_iv** – Harvard General Inquirer dictionary
   - **naive_bayes** – Machine learning classifier (Naive Bayes)
   - **logistic_regression** – Machine learning classifier (Logistic Regression)

2. **Positive threshold** (default ≥ 0.10) and **Negative threshold** (default ≤ −0.10) – These apply to all methods. Every sentiment approach produces a continuous score in [−1, +1]: dictionary methods use (positive words − negative words) / (positive + negative); ML methods use P(Positive) − P(Negative). The thresholds determine where the boundaries between Positive, Neutral, and Negative fall. Scores in between the two thresholds are classified as Neutral.

You must justify your threshold choices in your report. Consider that a very narrow neutral zone will produce very few Neutral classifications even when the sentiment signal is weak, while a very wide zone may misclassify genuinely positive or negative sentences. Your model choice determines which of the next two sub-steps you run.

### Step 6a – Dictionary Sentiment (if you chose lm_dictionary or harvard_iv)

Run this cell if you selected a dictionary-based model. It scores the full corpus and then evaluates the method against a set of 286 human-labelled seed sentences.

A classification metrics table (Precision, Recall, F1) and a confusion matrix are displayed. Both also appear as plain text below the table — select and copy this text to paste into your report. The confusion matrix updates live whenever you adjust the thresholds in Step 6.

**The classification metrics table and confusion matrix must appear in your written report**, along with a discussion of what the results reveal about the method's accuracy and limitations.

### Step 6b – ML Classifier Sentiment (if you chose naive_bayes or logistic_regression)

Run this cell if you selected a machine learning model. Rather than hard class labels, the classifier computes a net probability score — P(Positive) − P(Negative) — for each document. The thresholds set in Step 6 are then applied to categorise each document.

Performance is evaluated using **5-fold stratified cross-validation** across all 286 seed sentences, so every sentence is assessed by a model that was not trained on it. A classification metrics table (Precision, Recall, F1) and confusion matrix are displayed, both also in plain text for easy copying. The final model is trained on all 286 seed sentences before being applied to the full corpus.

**The classification metrics table and confusion matrix must appear in your written report**, along with a discussion of classifier performance and the implications of the threshold choices you made.

### Step 6c – Sentiment Score Table

Run this cell regardless of which model you chose. It produces a pivot table of sentiment scores with companies as rows and years as columns.

**This table must appear in your written report.** Copy or screenshot it. You must also write a substantive discussion of what the scores show.

### Step 7 – Select Secondary Metric

Run the cell and choose one of:

- **fog_index** – Gunning Fog readability index (measures text complexity)
- **cosine_similarity** – Year-on-year similarity of each firm's disclosures
- **lda** – Latent Dirichlet Allocation topic model

If you select **lda**, two additional inputs appear:

- **Number of topics** – Enter a value between 2 and 50. The default is 10. Consider how many coherent topics you expect in your corpus.
- **Topic label boxes** – One text box per topic. Leave these blank for now. You will fill them in after running Step 8, once you have seen the top words for each topic.

### Step 8 – Apply Secondary Metric

Run the cell. The selected metric is computed automatically.

If you chose LDA, this step may take 1–2 minutes. A progress indicator will be shown. Once complete, the top words for each topic are printed. Read these carefully and then go back to Step 7 to enter meaningful labels for each topic (e.g. "Liquidity Risk", "Regulatory Environment"). These labels will appear in your results table.

### Step 9 – Secondary Metric Score Table

Run this cell. It produces a pivot table equivalent to the one in Step 6c, but for your secondary metric. For cosine similarity, the table shows year pairs rather than individual years. For LDA, the table uses the topic labels you assigned.

**This table must appear in your written report.** Write a substantive discussion of what the results show.

### Step 10 – Visualisations

Run this cell. Two figures are generated and saved automatically:

- **fig1_sentiment.png** – A line chart showing mean sentiment scores by year (grouped by category) and a box plot showing the distribution of sentiment scores by category.
- **fig2_[metric].png** – Equivalent charts for your secondary metric.

To download the figures:

1. Click the **folder icon** in the left-hand panel of Colab to open the file browser.
2. Navigate to find the PNG files.
3. Right-click each file and select **Download**.

**Both figures must appear in your written report.** Write a discussion of what each figure shows.

### Step 11 – Manual Validation Sample

Run this cell. A file called **manual_validation_sample.csv** is generated. It contains 50 randomly selected sentences from the corpus. The columns are:

- `sentence_id` – Unique identifier
- `firm` – Company name
- `year` – Filing year
- `sentence_text` – The full sentence
- `automated_label` – The label assigned by your chosen sentiment model (1 = positive, 0 = neutral, −1 = negative)
- `human_label` – **This column is blank. You must fill it in.**

Download the file using the Colab file browser (same method as Step 10). Open it in Excel or Google Sheets. Read each sentence and enter your own label in the `human_label` column: 1, 0, or −1. Be consistent in how you apply the labels and explain your labelling criteria in your report.

**The completed table (all 50 rows with your human labels) must appear in your written report.** Discuss where your labels agree or disagree with the automated model and what this suggests about the model's performance.

### Step 12 – Submit Methodological Choices

Run this cell. It captures all of your widget selections — including your pre-processing choices, sentiment model, thresholds, secondary metric, and LDA settings if applicable — and submits them to the module log. This creates a record of your choices for the teaching team.

You do not need to do anything else here.

### Step 13 – Choices Summary Table

Run this cell. A formatted summary table of all your methodological choices is displayed. Copy this table into your written report. It must appear in your report alongside your written justification of each decision.

---

## 5. What to Download and Include in Your Report

Your written report must include all seven of the following. Missing items will be penalised.

| Item | Where it comes from | What you must write |
|------|---------------------|---------------------|
| Classification metrics table and confusion matrix | Step 6a or 6b | Discussion of model accuracy, which classes are hardest to predict, and what the results suggest about the method's suitability for your corpus |
| Sentiment score table | Step 6c | Discussion of patterns, trends, and what they suggest about your research theme |
| Secondary metric score table | Step 9 | Discussion of findings and what they add to the sentiment analysis |
| Sentiment chart (fig1_sentiment.png) | Step 10 | Discussion of visual patterns and what they show |
| Secondary metric chart (fig2_*.png) | Step 10 | Discussion of visual patterns |
| Completed manual validation table (50 rows) | Step 11, filled by you | Discussion of agreement/disagreement with automated labels and what this reveals |
| Methodological choices summary table | Step 13 | Justification of every choice you made |

To copy a table from the notebook output, use the plain-text version printed below each displayed table — select the text, copy, and paste into your document.

In addition, your report must include a discussion of your corpus section choice (item_1a vs item_7 or both) from Step 3.

---

## 6. Common Problems and Solutions

**The session has expired / the runtime disconnected.**
Colab sessions time out after around 90 minutes of inactivity. If you see a message saying the runtime has disconnected, go to Runtime > Reconnect. Once reconnected, you must run Step 0 again before continuing. Your widget choices (dropdowns, thresholds) will be reset, so you will need to re-enter them from Steps 4 onwards.

**I ran Step 0 but subsequent steps still fail.**
Make sure Step 0 fully completed before moving on. Look for a success message at the bottom of the Step 0 output. If you see an error instead, try running Step 0 again. If it continues to fail, check that your internet connection is active.

**The input box in Step 2 is not visible.**
The input box appears at the very bottom of the cell's output. Scroll down within the output area. If you still cannot see it, try clicking on the cell output area and scrolling within it.

**I entered the wrong student number in Step 2.**
Re-run Step 2 and enter the correct number. Your scenario is determined by your student number so it should be consistent as long as you enter your number correctly.

**The LDA step is taking a very long time.**
LDA can take 1–2 minutes depending on corpus size and the number of topics you requested. This is normal. Do not interrupt the cell while it is running. If it has been running for more than 5 minutes, try reducing the number of topics and re-running from Step 7.

**I cannot find the downloaded files.**
Files downloaded from Colab go to your browser's default download folder. Check your Downloads folder. If you accidentally closed Colab before downloading, re-run the notebook from Step 0 to regenerate the files (your choices will need to be re-entered).

**My figures look blank or incorrect.**
Make sure Steps 6–9 all completed successfully before running Step 10. If a required score or metric was not computed, the figures may not render correctly. Re-run the pipeline from Step 6 if needed.

**The Submit button in Step 12 gives an error.**
Check that you have an active internet connection. If the error persists, note down your choices from the Step 13 summary table and contact the module team.

---

If you encounter a problem not covered here, post in the module discussion forum on Moodle or contact your module tutor.
