# AG952 Workshop 3 — Pre-Session Testing Checklist

Run these four tests before every session, in order. Allow 20–30 minutes.
All tests assume the Apps Script has been deployed and the Web App URL has been
pasted into the student notebook. See `APPS_SCRIPT_SETUP.md` for setup instructions.

---

## Test 1 — Clean Environment Test

Confirms the student notebook runs without errors in a fresh Colab environment,
exactly as a student would experience it.

1. [ ] Open an **incognito browser window** (Chrome: Ctrl+Shift+N / Cmd+Shift+N).
2. [ ] Navigate to the student notebook sharing link:
       `https://colab.research.google.com/github/iamjamesbowden/AG952/blob/main/materials/week07/notebooks/AG952_Week07_Workshop3_StudentNotebook.ipynb`
3. [ ] Sign in to a Google account when prompted (any account is fine for this test).
4. [ ] Click **Runtime → Run all** (or press Ctrl+F9).
5. [ ] Wait for all cells to finish executing (the setup cell takes 2–3 minutes).
6. [ ] Confirm: **no red error boxes appear** in any cell.
7. [ ] Confirm: the CP0 team name dropdown is populated with team names.
8. [ ] Confirm: the pipeline diagram renders below the CP0 registration button.

---

## Test 2 — End-to-End Write Test

Confirms that a completed submission appears correctly in the Google Sheet.

1. [ ] In the same incognito window from Test 1 (or open a new one), navigate to
       the student notebook sharing link.
2. [ ] Run the setup cell, then run the constants cell.
3. [ ] **CP0**: Select team name **"The Write-Offs"** from the dropdown. Click Register.
       Confirm firm shows as **Boeing**.
4. [ ] **CP1**: Leave the section dropdown on **Item 1A (Risk Factors)**. Click Run.
       Confirm text is retrieved (cache or EDGAR).
5. [ ] **CP2**: Leave all defaults. Click Run. Confirm word cloud appears.
6. [ ] Run the CP2 feedback cell.
7. [ ] **CP3**: Leave defaults (L&M only). Click Run. Confirm sentiment score appears.
8. [ ] Run the CP3 feedback cell.
9. [ ] **CP4**: Leave defaults. Click Run. Confirm Fog scores appear.
10. [ ] Run the CP4 feedback cell.
11. [ ] **CP5**: Leave the default year pair. Click Run. Confirm similarity scores appear.
12. [ ] Run the CP5 feedback cell.
13. [ ] **CP6**: Type a short test note (at least 5 words, at most 150). Click Submit.
14. [ ] Confirm the notebook displays: **"Submitted successfully. Your results have
        been saved."**
15. [ ] Open the Google Sheet (`https://docs.google.com/spreadsheets/d/1UrgwAXYkJabGAsfI4uxAdTEKkHE5deHUbk7yxvF9DBg`).
16. [ ] Confirm a new row has appeared in **Sheet1**.
17. [ ] Confirm the row contains correct values in the correct columns:
        - `team_name` = "The Write-Offs"
        - `firm` = "Boeing"
        - `analyst_note` = the note you typed
        - `timestamp` = approximately the current UTC time
        - All other columns contain non-empty values.

---

## Test 3 — Concurrent Write Test

Confirms that simultaneous submissions from two students do not overwrite each other.

1. [ ] Open **two separate incognito windows** simultaneously.
2. [ ] Load the student notebook sharing link in both windows.
3. [ ] In **Window A**: complete the notebook through to CP6 using team name
       **"Item 1A-OK"** (firm: Boeing). Do not click Submit yet.
4. [ ] In **Window B**: complete the notebook through to CP6 using team name
       **"The Going Concerns"** (firm: Boeing). Do not click Submit yet.
5. [ ] Click Submit in **Window A**, then immediately (within 5 seconds) click Submit
       in **Window B**.
6. [ ] Confirm both windows show the success message.
7. [ ] Open the Google Sheet and confirm **two separate rows** now exist — one for
       each team — with no data from one row overwriting the other.

---

## Test 4 — Facilitator Notebook Test

Confirms the facilitator debrief notebook processes the test data without errors.

1. [ ] Ensure at least two rows of test data are in the sheet (from Tests 2 and 3).
2. [ ] Open the facilitator debrief notebook in Colab:
       `https://colab.research.google.com/github/iamjamesbowden/AG952/blob/main/materials/week07/notebooks/AG952_Week07_Workshop3_FacilitatorDebrief.ipynb`
3. [ ] Ensure `GSHEET_CREDS` is set in Colab Secrets for this session (service account
       JSON with read access to the sheet).
4. [ ] Run all cells top to bottom.
5. [ ] Confirm: data pull cell loads the rows and shows no missing-column warnings.
6. [ ] Confirm: all Part 1 visualisations render (decision table, heatmap, pie chart,
       frame distribution, TF/TF-IDF scatter).
7. [ ] Confirm: all Part 2 visualisations render (sentiment scatter, Fog trajectories,
       similarity heatmap, analyst note word cloud, divergence table).
8. [ ] No cells raise an unhandled exception.

**Before the session:** Delete all test rows from Sheet1 so the debrief starts with
a clean dataset. Keep the header row in row 1.

---

## Notes

- If Test 2 or 3 fails at the submit step with "Submission failed", check that the
  Web App URL in the student notebook is correct and that the Apps Script endpoint
  returns "AG952 Workshop 3 — endpoint active" when visited in a browser.
- If Test 4 produces column-not-found errors in the facilitator notebook, this
  indicates a mismatch between the sheet column names and the facilitator notebook's
  `EXPECTED_COLS` configuration. Verify that the sheet header row matches the
  column names set in the facilitator notebook's Configuration cell.
- Re-run all four tests if the student notebook is modified after initial testing.
