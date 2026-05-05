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
