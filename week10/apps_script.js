/**
 * AG952 Week 10 — Workshop Submission Handler
 * Deploy as a Google Apps Script Web App (Execute as: Me, Access: Anyone)
 *
 * Sheet structure:
 *   "Teams"       — registered teams (col A: team_name, col B: registered_at)
 *   "Round1"      — raw submissions (team_name, timestamp, call, chips, prediction, reasoning)
 *   "Round2"      — signal classifications (team_name, timestamp, call, classification)
 *   "Round3"      — final predictions (same as Round1 format)
 *   "Leaderboard" — public leaderboard (written ONLY after all teams submit each round)
 *   "Reflections" — personal reflections (team_name, timestamp, q1, q2, q3)
 */

const SHEET_ID = "1eEVTNHUXFg6covor9kE2sf5_1235ZW-u930152c_-TA";

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const action = data.action;
    const ss = SpreadsheetApp.openById(SHEET_ID);
    let result = {};

    if (action === "register_team") {
      result = registerTeam(ss, data);
    } else if (action === "submit_round1") {
      result = submitRound(ss, data, "Round1", 1);
    } else if (action === "submit_round2") {
      result = submitRound(ss, data, "Round2", 2);
    } else if (action === "submit_round3") {
      result = submitRound(ss, data, "Round3", 3);
    } else if (action === "submit_reflection") {
      result = submitReflection(ss, data);
    } else if (action === "get_status") {
      result = getStatus(ss, data);
    } else if (action === "get_leaderboard") {
      result = getLeaderboard(ss);
    }

    return ContentService.createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      success: false, error: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

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
  const sheet = ss.getSheetByName(sheetName);
  const teamsSheet = ss.getSheetByName("Teams");
  const teamName = data.team_name;

  // Prevent double submission
  const existing = sheet.getDataRange().getValues();
  const alreadySubmitted = existing.some(r => r[0] === teamName);
  if (alreadySubmitted) {
    return { success: false, message: "already_submitted" };
  }

  // Write submission rows (one per call)
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

  // Check if all teams have now submitted this round
  lockPredictionsUntilAllTeamsSubmit(ss, roundNumber);

  return { success: true, message: "submitted" };
}

/**
 * Writes predictions to the public Leaderboard tab only after all registered
 * teams have a submission for the given round number.
 */
function lockPredictionsUntilAllTeamsSubmit(ss, roundNumber) {
  const teamsSheet = ss.getSheetByName("Teams");
  const allTeams = teamsSheet.getDataRange().getValues()
    .slice(1)  // skip header
    .map(r => r[0])
    .filter(t => t !== "");

  const roundSheetName = `Round${roundNumber}`;
  const roundSheet = ss.getSheetByName(roundSheetName);
  const submissions = roundSheet.getDataRange().getValues()
    .slice(1)
    .map(r => r[0]);

  const teamsSubmitted = [...new Set(submissions)];
  const allSubmitted = allTeams.every(t => teamsSubmitted.includes(t));

  if (!allSubmitted) return; // Not all teams in yet — hold off

  // All teams submitted: write to Leaderboard
  const lbSheet = ss.getSheetByName("Leaderboard");
  // Clear only this round's section, then rewrite
  // For simplicity, append a "round marker" row and all team data
  lbSheet.appendRow([`--- Round ${roundNumber} complete ---`]);
  const allRows = roundSheet.getDataRange().getValues().slice(1);
  for (const row of allRows) {
    lbSheet.appendRow([`R${roundNumber}`, ...row]);
  }
}

function submitReflection(ss, data) {
  const sheet = ss.getSheetByName("Reflections");
  sheet.appendRow([
    data.team_name, new Date().toISOString(),
    data.q1, data.q2, data.q3
  ]);
  return { success: true };
}

function getStatus(ss, data) {
  const roundSheetName = `Round${data.round}`;
  const roundSheet = ss.getSheetByName(roundSheetName);
  const teamsSheet = ss.getSheetByName("Teams");
  const allTeams = teamsSheet.getDataRange().getValues().slice(1).map(r => r[0]).filter(t => t);
  const submitted = [...new Set(
    roundSheet.getDataRange().getValues().slice(1).map(r => r[0]).filter(t => t)
  )];
  return {
    success: true,
    all_teams: allTeams,
    submitted_teams: submitted,
    total: allTeams.length,
    submitted_count: submitted.length,
    all_submitted: allTeams.every(t => submitted.includes(t))
  };
}

function getLeaderboard(ss) {
  const lbSheet = ss.getSheetByName("Leaderboard");
  const data = lbSheet.getDataRange().getValues();
  return { success: true, leaderboard: data };
}
