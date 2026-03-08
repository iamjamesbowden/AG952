// AG952 Assignment 2026 — Methodological Choices Logger
// Deploy as: Execute as Me | Anyone can access (no sign-in required)
// Replace SHEET_ID below with your Google Sheets spreadsheet ID before deploying.

const SHEET_ID = 'YOUR_SPREADSHEET_ID_HERE';
const SHEET_NAME = 'choices';

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);

    // Write header row if sheet is empty
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        'timestamp',
        'student_id',
        'scenario',
        'tokenisation_method',
        'stopword_list',
        'normalisation_method',
        'number_handling',
        'tfidf_weighting',
        'sentiment_model',
        'secondary_metric',
        'naive_bayes',
        'submission_count'
      ]);
    }

    // Count prior submissions from this student
    const allData = sheet.getDataRange().getValues();
    const priorCount = allData.filter(
      row => String(row[1]) === String(data.student_id)
    ).length;

    sheet.appendRow([
      new Date().toISOString(),
      data.student_id,
      data.scenario,
      data.tokenisation_method,
      data.stopword_list,
      data.normalisation_method,
      data.number_handling,
      data.tfidf_weighting,
      data.sentiment_model,
      data.secondary_metric,
      data.naive_bayes,
      priorCount + 1
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({ status: 'success', submission: priorCount + 1 }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: 'error', message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
