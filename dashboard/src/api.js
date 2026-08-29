// api.js — talks to the BotMedic control API.
//
// The dashboard degrades in three steps so it is always demoable:
//   1. the live control API (approve, reject and demo runs all work)
//   2. the incidents.json the engine writes (real data, read only)
//   3. bundled mock data (nothing running at all)

import { MOCK_FEED } from './mockData.js'

export const API_BASE = 'http://127.0.0.1:8100'

export const SOURCE = {
  LIVE: 'live',
  FILE: 'file',
  MOCK: 'mock',
}

async function getJson(url, options) {
  const response = await fetch(url, { cache: 'no-store', ...options })
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}))
    const error = new Error(detail.error || `Request failed (${response.status})`)
    error.status = response.status
    throw error
  }
  return response.json()
}

/** Load the incident feed, falling back through the three sources. */
export async function loadFeed() {
  try {
    const feed = await getJson(`${API_BASE}/api/feed`)
    return { feed, source: SOURCE.LIVE }
  } catch (liveError) {
    try {
      const feed = await getJson('/incidents.json')
      return { feed, source: SOURCE.FILE }
    } catch (fileError) {
      return { feed: MOCK_FEED, source: SOURCE.MOCK }
    }
  }
}

/** Break scenarios and the bot fleet, for the run launcher. */
export async function loadScenarios() {
  return getJson(`${API_BASE}/api/scenarios`)
}

/** Whether the engine is mid-run. */
export async function loadStatus() {
  return getJson(`${API_BASE}/api/status`)
}

/** Break the site and run a bot through the healing loop. */
export async function startRun(botId, scenario) {
  return getJson(`${API_BASE}/api/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bot_id: botId, scenario }),
  })
}

/** Apply a verified patch to the real script and re-run the bot. */
export async function approveIncident(runId, scenario) {
  return getJson(`${API_BASE}/api/incidents/${runId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario }),
  })
}

/** Discard a proposed patch without touching the script. */
export async function rejectIncident(runId, reason) {
  return getJson(`${API_BASE}/api/incidents/${runId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  })
}


