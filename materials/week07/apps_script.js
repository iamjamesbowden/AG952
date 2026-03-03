// AG952 Workshop 3 — Google Apps Script web endpoint
// ---------------------------------------------------------------------------
// Deploy this as a Web App in Google Apps Script:
//   Execute as: Me
//   Who has access: Anyone
// See APPS_SCRIPT_SETUP.md for step-by-step deployment instructions.
// ---------------------------------------------------------------------------

var SPREADSHEET_ID = "1UrgwAXYkJabGAsfI4uxAdTEKkHE5deHUbk7yxvF9DBg";
var SHEET_NAME     = "Sheet1";

/**
 * doPost: receives a JSON payload from the student notebook and appends one
 * row to the target sheet. Returns {"status":"success"} or {"status":"error"}.
 */
function doPost(e) {
  try {
    var data  = JSON.parse(e.postData.contents);
    var sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_NAME);

    if (!sheet) {
      throw new Error(
        "Sheet '" + SHEET_NAME + "' not found in spreadsheet " + SPREADSHEET_ID +
        ". Create a tab named '" + SHEET_NAME + "' with the correct header row."
      );
    }

    // Column order must match the header row in the sheet exactly.
    var row = [
      data.student_id         || "",
      data.team_name          || "",
      data.firm               || "",
      data.year               || "",
      data.section            || "",
      data.normalisation      || "",
      data.stopwords          || "",
      data.remove_numbers     || "",
      data.lowercase          || "",
      data.dictionary         || "",
      data.net_sentiment_lm   || "",
      data.net_sentiment_hiv4 || "",
      data.fog_score          || "",
      data.readability_frame  || "",
      data.cosine_similarity  || "",
      data.tf_or_tfidf        || "",
      data.comparison_pair    || "",
      data.analyst_note       || "",
      data.timestamp          || new Date().toISOString()
    ];

    sheet.appendRow(row);

    return ContentService
      .createTextOutput(JSON.stringify({ "status": "success" }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ "status": "error", "message": err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * doGet: health-check endpoint. Visit the Web App URL in a browser to confirm
 * the script is deployed and reachable before the session.
 */
function doGet(e) {
  return ContentService
    .createTextOutput("AG952 Workshop 3 — endpoint active")
    .setMimeType(ContentService.MimeType.TEXT);
}
