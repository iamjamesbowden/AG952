/**
 * AG952 Week 10 — Workshop Submission Handler
 * Deploy as a Google Apps Script Web App (Execute as: Me, Access: Anyone)
 *
 * Sheet tabs required:
 *   "Teams"       — team_name, registered_at
 *   "Round1"      — team_name, timestamp, quarter, chips, prediction, reasoning
 *   "Round2"      — team_name, timestamp, quarter, classification
 *   "Round3"      — team_name, timestamp, quarter, chips, prediction, reasoning
 *   "Leaderboard" — written automatically once all teams submit (or instructor forces)
 *   "Reflections" — team_name, timestamp, q1, q2, q3
 *
 * Instructor-only actions (require instructor_key):
 *   force_unlock_round   — write leaderboard immediately regardless of submission count
 *   get_round_data       — fetch all rows from a round sheet
 *   get_reflections_data — fetch all reflection rows
 */

const SHEET_ID      = "1eEVTNHUXFg6covor9kE2sf5_1235ZW-u930152c_-TA";
const INSTRUCTOR_KEY = "AG952_2026";  // Change this before deployment

function doPost(e) {
  try {
    const data   = JSON.parse(e.postData.contents);
    const action = data.action;
    const ss     = SpreadsheetApp.openById(SHEET_ID);
    let result   = {};

    if      (action === "register_team")       result = registerTeam(ss, data);
    else if (action === "submit_round1")        result = submitRound(ss, data, "Round1", 1);
    else if (action === "submit_round2")        result = submitRound(ss, data, "Round2", 2);
    else if (action === "submit_round3")        result = submitRound(ss, data, "Round3", 3);
    else if (action === "submit_reflection")    result = submitReflection(ss, data);
    else if (action === "get_status")           result = getStatus(ss, data);
    else if (action === "get_leaderboard")      result = getLeaderboard(ss);
    else if (action === "force_unlock_round")   result = forceUnlockRound(ss, data);
    else if (action === "get_round_data")       result = getRoundData(ss, data);
    else if (action === "get_reflections_data") result = getReflectionsData(ss, data);
    else result = { success: false, error: "Unknown action: " + action };

    return ContentService.createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      success: false, error: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// ── Student actions ───────────────────────────────────────────────────────────

function registerTeam(ss, data) {
  const sheet = ss.getSheetByName("Teams");
  const teams = sheet.getDataRange().getValues().map(r => r[0]);
  if (teams.includes(data.team_name)) {
    return { success: true, message: "already_registered" };
  }
  sheet.appendRow([data.team_name, new Date().toISOString()]);
  return { success: true, message: "registered" };
}

function submitRound(ss, data, sheetName, roundNumber) {
  const sheet    = ss.getSheetByName(sheetName);
  const teamName = data.team_name;

  // Prevent double submission
  const existing       = sheet.getDataRange().getValues();
  const alreadySubmitted = existing.some(r => r[0] === teamName);
  if (alreadySubmitted) {
    return { success: false, message: "already_submitted" };
  }

  const ts = new Date().toISOString();
  if (roundNumber === 1 || roundNumber === 3) {
    for (const callData of data.calls) {
      sheet.appendRow([
        teamName, ts,
        callData.quarter, callData.chips, callData.prediction, callData.reasoning
      ]);
    }
  } else if (roundNumber === 2) {
    for (const callData of data.calls) {
      sheet.appendRow([teamName, ts, callData.quarter, callData.classification]);
    }
  }

  checkAndLockRound(ss, roundNumber, false);
  return { success: true, message: "submitted" };
}

function submitReflection(ss, data) {
  const sheet = ss.getSheetByName("Reflections");
  sheet.appendRow([
    data.team_name, new Date().toISOString(),
    data.q1, data.q2, data.q3
  ]);
  return { success: true };
}

// ── Lock logic ────────────────────────────────────────────────────────────────

/**
 * Writes round data to the Leaderboard tab.
 * Runs automatically when all teams submit; instructor can force it early.
 * Safe to call multiple times — checks for duplicate marker before writing.
 */
function checkAndLockRound(ss, roundNumber, force) {
  const teamsSheet = ss.getSheetByName("Teams");
  const allTeams   = teamsSheet.getDataRange().getValues()
    .slice(1).map(r => r[0]).filter(t => t !== "");

  const roundSheet  = ss.getSheetByName("Round" + roundNumber);
  const submissions = roundSheet.getDataRange().getValues()
    .slice(1).map(r => r[0]).filter(t => t !== "");

  const teamsSubmitted = [...new Set(submissions)];
  const allSubmitted   = allTeams.length > 0 &&
                         allTeams.every(t => teamsSubmitted.includes(t));

  if (!allSubmitted && !force) return;

  // Guard against double-write
  const lbSheet   = ss.getSheetByName("Leaderboard");
  const lbData    = lbSheet.getDataRange().getValues();
  const marker    = "--- Round " + roundNumber + " complete ---";
  if (lbData.some(r => r[0] === marker)) return;

  lbSheet.appendRow([marker]);
  const allRows = roundSheet.getDataRange().getValues().slice(1);
  for (const row of allRows) {
    lbSheet.appendRow(["R" + roundNumber, ...row]);
  }
}

// ── Instructor actions ────────────────────────────────────────────────────────

function forceUnlockRound(ss, data) {
  if (data.instructor_key !== INSTRUCTOR_KEY) {
    return { success: false, error: "Unauthorized" };
  }
  const round = parseInt(data.round);
  if (isNaN(round) || round < 1 || round > 3) {
    return { success: false, error: "round must be 1, 2, or 3" };
  }
  checkAndLockRound(ss, round, true);

  const roundSheet = ss.getSheetByName("Round" + round);
  const rows       = roundSheet.getDataRange().getValues().slice(1);
  const submitted  = [...new Set(rows.map(r => r[0]).filter(t => t !== ""))];
  return {
    success: true,
    message: "Round " + round + " force-unlocked",
    teams_included: submitted.length,
    teams_included_names: submitted
  };
}

function getStatus(ss, data) {
  const roundSheetName = "Round" + data.round;
  const roundSheet     = ss.getSheetByName(roundSheetName);
  const teamsSheet     = ss.getSheetByName("Teams");
  const allTeams       = teamsSheet.getDataRange().getValues()
    .slice(1).map(r => r[0]).filter(t => t);
  const submitted = [...new Set(
    roundSheet.getDataRange().getValues().slice(1).map(r => r[0]).filter(t => t)
  )];
  const notSubmitted = allTeams.filter(t => !submitted.includes(t));
  return {
    success: true,
    all_teams: allTeams,
    submitted_teams: submitted,
    not_submitted: notSubmitted,
    total: allTeams.length,
    submitted_count: submitted.length,
    all_submitted: allTeams.length > 0 && allTeams.every(t => submitted.includes(t))
  };
}

function getRoundData(ss, data) {
  if (data.instructor_key !== INSTRUCTOR_KEY) {
    return { success: false, error: "Unauthorized" };
  }
  const round = parseInt(data.round);
  const sheet = ss.getSheetByName("Round" + round);
  if (!sheet) return { success: false, error: "Round" + round + " sheet not found" };
  const rows = sheet.getDataRange().getValues();
  return { success: true, rows: rows.length > 1 ? rows.slice(1) : [] };
}

function getReflectionsData(ss, data) {
  if (data.instructor_key !== INSTRUCTOR_KEY) {
    return { success: false, error: "Unauthorized" };
  }
  const sheet = ss.getSheetByName("Reflections");
  if (!sheet) return { success: false, error: "Reflections sheet not found" };
  const rows = sheet.getDataRange().getValues();
  return { success: true, rows: rows.length > 1 ? rows.slice(1) : [] };
}

function getLeaderboard(ss) {
  const lbSheet = ss.getSheetByName("Leaderboard");
  const data    = lbSheet.getDataRange().getValues();
  return { success: true, leaderboard: data };
}
