const BASE = ''

export async function fetchCases() {
  const r = await fetch(`${BASE}/api/cases`)
  if (!r.ok) throw new Error(`GET /api/cases failed: ${r.status}`)
  return r.json()
}

export async function fetchCase(caseId) {
  const r = await fetch(`${BASE}/api/cases/${caseId}`)
  if (!r.ok) throw new Error(`GET /api/cases/${caseId} failed: ${r.status}`)
  return r.json()
}

export async function fetchStats() {
  const r = await fetch(`${BASE}/api/stats`)
  if (!r.ok) throw new Error(`GET /api/stats failed: ${r.status}`)
  return r.json()
}

export async function fetchHandwerker(caseId) {
  const r = await fetch(`${BASE}/api/cases/${caseId}/handwerker`)
  if (!r.ok) throw new Error(`GET handwerker failed: ${r.status}`)
  return r.json()
}

export async function assignHandwerker(caseId, handwerkerId) {
  const r = await fetch(`${BASE}/api/cases/${caseId}/assign_handwerker`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ handwerker_id: handwerkerId }),
  })
  if (!r.ok) throw new Error(`POST assign_handwerker failed: ${r.status}`)
  return r.json()
}
