# AG952 Workshop 3 — Google Apps Script Deployment Instructions

This document explains how to deploy the `apps_script.js` file as a Google Apps Script
Web App so that the student notebook can write results directly to the Google Sheet
without requiring credentials in each student's Colab environment.

---

## Prerequisites

- You must be signed in to the Google account that owns the spreadsheet
  `1UrgwAXYkJabGAsfI4uxAdTEKkHE5deHUbk7yxvF9DBg`.
- The target spreadsheet must have a tab named **Sheet1** with the following header
  row in row 1, columns A through S:

```
student_id | team_name | firm | year | section | normalisation | stopwords |
remove_numbers | lowercase | dictionary | net_sentiment_lm | net_sentiment_hiv4 |
fog_score | readability_frame | cosine_similarity | tf_or_tfidf |
comparison_pair | analyst_note | timestamp
```

  You can add this header row manually or by pasting the following into cell A1:

```
student_id	team_name	firm	year	section	normalisation	stopwords	remove_numbers	lowercase	dictionary	net_sentiment_lm	net_sentiment_hiv4	fog_score	readability_frame	cosine_similarity	tf_or_tfidf	comparison_pair	analyst_note	timestamp
```

---

## Step 1 — Open Google Apps Script

1. Go to **https://script.google.com**
2. Click **New project** (top left).
3. The editor opens with a default `function myFunction() {}` stub.

---

## Step 2 — Paste the Script

1. Select all the default code in the editor and delete it.
2. Open the file `apps_script.js` from this repository
   (`materials/week07/apps_script.js`).
3. Copy the entire contents and paste them into the Apps Script editor.
4. Verify that `SPREADSHEET_ID` at the top of the script matches your spreadsheet:
   ```javascript
   var SPREADSHEET_ID = "1UrgwAXYkJabGAsfI4uxAdTEKkHE5deHUbk7yxvF9DBg";
   var SHEET_NAME     = "Sheet1";
   ```
5. Click the **floppy-disk icon** (or press Ctrl+S / Cmd+S) to save.
   Give the project a name such as `AG952 Workshop 3`.

---

## Step 3 — Deploy as a Web App

1. Click **Deploy** (top right) → **New deployment**.
2. Click the gear icon next to **Type** and select **Web app**.
3. Set the following:
   - **Description**: `AG952 Workshop 3 student submission endpoint`
   - **Execute as**: **Me** (your Google account)
   - **Who has access**: **Anyone**
4. Click **Deploy**.
5. You will be asked to **authorise** the script to access your Google Sheets.
   Click **Authorise access**, choose your account, and click **Allow**.
6. After authorisation, the deployment dialog shows a **Web App URL**.
   It looks like:
   ```
   https://script.google.com/macros/s/AKfycb.../exec
   ```
7. **Copy this URL.** You will need it in Step 4.

---

## Step 4 — Paste the URL into the Student Notebook

1. Open `AG952_Week07_Workshop3_StudentNotebook.ipynb` (in this repository or in
   Google Colab).
2. Find the cell labelled **Instructor configuration -- paste Web App URL before
   session**. It is directly below the TEAM_ASSIGNMENT cell and contains:
   ```python
   APPS_SCRIPT_URL = "[PASTE YOUR WEB APP URL HERE — see APPS_SCRIPT_SETUP.md]"
   ```
3. Replace the placeholder with the URL you copied in Step 3:
   ```python
   APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycb.../exec"
   ```
4. Save the notebook and commit the change, or distribute the updated notebook
   to students directly.

---

## Step 5 — Test the Endpoint

Before the session, confirm the script is live:

1. Open the Web App URL in any browser.
2. You should see the plain-text response:
   ```
   AG952 Workshop 3 — endpoint active
   ```
   If you see an error or a blank page, re-check the deployment settings in Step 3
   and ensure the script was saved before deploying.

---

## Re-deploying After Changes

If you edit the script after the initial deployment, you must create a **new
deployment** (Deploy → New deployment) rather than updating the existing one,
or the changes will not take effect for students. Update `APPS_SCRIPT_URL` in
the notebook to the new URL if it changes.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Browser shows "Script function not found: doGet" | Script was not saved before deploying | Save the script, then create a new deployment |
| Student notebook shows "endpoint not configured" | APPS_SCRIPT_URL still contains the placeholder | Paste the real URL into the config cell |
| Student notebook shows "Submission failed" | Network timeout or Apps Script cold start | Click Retry; if repeated, check the endpoint URL |
| Sheet row appears but columns are shifted | Header row missing or in wrong column | Add the header row to row 1 of Sheet1 |
| "Sheet 'Sheet1' not found" error | Tab is named something other than Sheet1 | Rename the tab or update SHEET_NAME in the script |
