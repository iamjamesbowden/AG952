// AG952 Workshop 9 — Google Apps Script web endpoint
// ---------------------------------------------------------------------------
// Deploy this as a Web App in Google Apps Script:
//   Execute as: Me
//   Who has access: Anyone
// See APPS_SCRIPT_SETUP.md for step-by-step deployment instructions.
// ---------------------------------------------------------------------------

var SPREADSHEET_ID = "";   // paste your Google Sheet ID here before deploying
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
      data.team_name                  || "",
      data.cp1_period                 || "",
      data.cp2_normalisation          || "",
      data.cp2_stopwords              || "",
      data.cp2_remove_numbers         || "",
      data.cp2_lowercase              || "",
      data.cp2b_n_clusters            || "",
      data.cp2b_cluster_names         || "",
      data.cp3_n_topics               || "",
      data.cp3_topic_labels           || "",
      data.cp4_dictionary             || "",
      data.cp4_sentiment_2010_2014    || "",
      data.cp4_sentiment_2019_2025    || "",
      data.cp6_model                  || "",
      data.cp6_finbert_accuracy       || "",
      data.cp6_distilbert_accuracy    || "",
      data.cp7_interpretability_choice|| "",
      data.cp8_analyst_note           || "",
      data.timestamp                  || new Date().toISOString()
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
 * doGet: health-check endpoint. Returns the current UTC timestamp.
 */
function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({
      "status": "ok",
      "workshop": "AG952 Workshop 9 — BrewDog Transformer",
      "time": new Date().toISOString()
    }))
    .setMimeType(ContentService.MimeType.JSON);
}
