# AG952 Workshop 9 — Apps Script Setup Guide

## Google Sheet setup

1. Create a new Google Sheet for this workshop.
2. Rename the first tab **Sheet1**.
3. Add the following header row in row 1 (one value per column, exactly as written):

```
team_name | cp1_period | cp2_normalisation | cp2_stopwords | cp2_remove_numbers | cp2_lowercase | cp2b_n_clusters | cp2b_cluster_names | cp3_n_topics | cp3_topic_labels | cp4_dictionary | cp4_sentiment_2010_2014 | cp4_sentiment_2019_2025 | cp6_model | cp6_finbert_accuracy | cp6_distilbert_accuracy | cp7_interpretability_choice | cp8_analyst_note | timestamp
```

4. Copy the Sheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/**[SHEET ID]**/edit`

---

## Apps Script deployment

1. In the Google Sheet, go to **Extensions → Apps Script**.
2. Delete any existing code in the editor.
3. Paste the contents of `apps_script.js` from this directory.
4. Replace the empty `SPREADSHEET_ID` string with your Sheet ID.
5. Click **Save** (floppy disk icon).
6. Click **Deploy → New deployment**.
7. Click the gear icon next to **Select type** and choose **Web App**.
8. Set:
   - **Execute as:** Me
   - **Who has access:** Anyone
9. Click **Deploy**.
10. Copy the **Web App URL** — this is your `APPS_SCRIPT_URL`.

---

## Configure the student notebook

Open `AG952_W9_BrewDog_Transformer_Student.ipynb` and paste the URL into the Config cell:

```python
APPS_SCRIPT_URL = "https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec"
```

---

## Configure the facilitator notebook

Open `AG952_W9_BrewDog_Facilitator.ipynb` and set:

```python
SPREADSHEET_ID = "YOUR_SHEET_ID"
WORKSHEET_NAME = "Sheet1"
```

The facilitator notebook reads from the sheet using a Google service account stored in Colab Secrets as `GSHEET_CREDS`. See the Week 7 setup guide for instructions on creating and storing service account credentials.

---

## Pre-session checklist

- [ ] Google Sheet created with correct header row
- [ ] Apps Script deployed and URL confirmed with a browser GET request
- [ ] `APPS_SCRIPT_URL` pasted into the student notebook and re-committed to GitHub
- [ ] Student notebook opened and Step 0 tested end-to-end
- [ ] CP1 data load tested (confirms the CSV URL is accessible)
- [ ] CP5 transformer download tested — first run downloads ~420 MB; Colab may need GPU runtime
- [ ] Facilitator notebook configured with Sheet ID and service account credentials
- [ ] Team names configured in the `TEAM_ASSIGNMENT` dict in the student notebook
