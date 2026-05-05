import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchCases, fetchStats } from '../api'

const FILTERS = [
  { key: 'all', label: 'Alle' },
  { key: 'emergency', label: 'Notfall' },
  { key: 'normal', label: 'Normal' },
  { key: 'low', label: 'Niedrig' },
]

const PRIORITY_DOT = {
  emergency: 'bg-error shadow-[0_0_8px_rgba(186,26,26,0.6)] animate-pulse',
  normal: 'bg-secondary',
  low: 'bg-outline-variant',
}

const URGENCY_STYLE = {
  kritisch: 'bg-error/15 text-error border-error/30',
  hoch: 'bg-error/10 text-error border-error/20',
  mittel: 'bg-secondary/15 text-on-secondary-container border-secondary/30',
  niedrig: 'bg-outline/10 text-on-surface-variant border-outline/20',
}

function UrgencyBadge({ triage, pending }) {
  if (pending) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-surface-variant text-on-surface-variant border border-outline-variant/40">
        <span className="material-symbols-outlined text-[12px] animate-spin">progress_activity</span>
        KI bewertet…
      </span>
    )
  }
  if (!triage?.urgency) return null
  const cls = URGENCY_STYLE[triage.urgency.toLowerCase()] || URGENCY_STYLE.niedrig
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium border capitalize ${cls}`}
    >
      <span className="material-symbols-outlined text-[12px]">priority_high</span>
      {triage.urgency}
    </span>
  )
}

export default function Dashboard() {
  const [cases, setCases] = useState([])
  const [stats, setStats] = useState(null)
  const [filter, setFilter] = useState('all')
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const [c, s] = await Promise.all([fetchCases(), fetchStats()])
        if (!active) return
        setCases(c)
        setStats(s)
        setError(null)
      } catch (e) {
        if (active) setError(e.message)
      }
    }
    load()
    const id = setInterval(load, 4000)
    return () => {
      active = false
      clearInterval(id)
    }
  }, [])

  const filtered = useMemo(
    () => (filter === 'all' ? cases : cases.filter((c) => c.priority === filter)),
    [cases, filter],
  )

  const counts = useMemo(() => {
    const out = { emergency: 0, normal: 0, low: 0 }
    cases.forEach((c) => {
      out[c.priority] = (out[c.priority] || 0) + 1
    })
    return out
  }, [cases])

  const criticalCase = cases.find((c) => c.priority === 'emergency')

  return (
    <div className="p-margin-desktop">
      <div className="flex justify-between items-end mb-gutter">
        <div>
          <h1 className="text-h1 text-on-surface mb-xs">Operational Overview</h1>
          <p className="text-body-md text-on-surface-variant">
            Manage and track all ongoing property operations.
          </p>
        </div>
        <div className="flex items-center gap-2 bg-surface-container-high p-1 rounded-lg border border-outline-variant/30">
          {FILTERS.map((f) => {
            const active = filter === f.key
            const count = f.key === 'all' ? cases.length : counts[f.key] || 0
            return (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={`px-4 py-1.5 rounded-md text-label-md flex items-center gap-1 transition-colors ${
                  active
                    ? 'bg-white shadow-sm text-primary-container border border-outline-variant/50'
                    : 'text-on-surface-variant hover:bg-surface-variant'
                }`}
              >
                {f.label}
                {f.key !== 'all' && (
                  <span
                    className={`px-1.5 rounded text-[10px] ${
                      f.key === 'emergency'
                        ? 'bg-error/10 text-error'
                        : f.key === 'normal'
                        ? 'bg-secondary/10 text-secondary'
                        : 'bg-outline/10 text-outline'
                    }`}
                  >
                    {count}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      <div className="grid grid-cols-12 gap-gutter mb-gutter">
        <StatCard
          label="Offene Vorgänge"
          value={stats?.open_cases ?? cases.length}
          icon="assignment_late"
          accent="primary-container"
        />
        <StatCard
          label="Notfall / Hoch"
          value={counts.emergency}
          icon="priority_high"
          accent="error"
        />
        <CriticalAlert critical={criticalCase} onClick={() => criticalCase && navigate(`/vorgang/${criticalCase.id}`)} />
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant/50 rounded-xl shadow-sm overflow-hidden">
        <div className="px-md py-4 border-b border-outline-variant/50 bg-surface-container-low flex justify-between items-center">
          <h2 className="text-h3 text-on-surface">Recent Cases</h2>
          <span className="text-label-sm text-on-surface-variant">
            Live · alle 4 Sekunden aktualisiert
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-outline-variant/30 text-on-surface-variant text-label-sm uppercase tracking-wider bg-surface-bright">
                <th className="py-3 px-4 font-medium w-12 text-center">Status</th>
                <th className="py-3 px-4 font-medium">ID</th>
                <th className="py-3 px-4 font-medium">Adresse</th>
                <th className="py-3 px-4 font-medium">Mieter</th>
                <th className="py-3 px-4 font-medium">Mangel</th>
                <th className="py-3 px-4 font-medium">KI-Empfehlung</th>
                <th className="py-3 px-4 font-medium">Zeit</th>
                <th className="py-3 px-4 font-medium text-right">Aktionen</th>
              </tr>
            </thead>
            <tbody className="text-body-sm text-on-surface divide-y divide-outline-variant/20">
              {error && (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-error">
                    Fehler beim Laden: {error}. Läuft die API auf Port 8000?
                  </td>
                </tr>
              )}
              {!error && filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-on-surface-variant">
                    Noch keine Vorgänge erfasst. Sobald der Chatbot eine Meldung
                    abschließt, erscheint sie hier.
                  </td>
                </tr>
              )}
              {filtered.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => navigate(`/vorgang/${c.id}`)}
                  className="hover:bg-surface-container-low transition-colors group cursor-pointer"
                >
                  <td className="py-4 px-4 text-center">
                    <div
                      className={`w-3 h-3 rounded-full mx-auto ${PRIORITY_DOT[c.priority]}`}
                    />
                  </td>
                  <td className="py-4 px-4 text-label-md text-on-surface-variant">
                    #{c.id}
                  </td>
                  <td className="py-4 px-4">
                    <span className="block font-medium">
                      {c.tenant?.adresse || '—'}
                    </span>
                    <span className="text-on-surface-variant text-[12px]">
                      {c.mietertyp ? c.mietertyp[0].toUpperCase() + c.mietertyp.slice(1) : ''}
                    </span>
                  </td>
                  <td className="py-4 px-4">{c.tenant?.name || '—'}</td>
                  <td className="py-4 px-4">
                    <span className="font-medium text-on-surface">
                      {c.mangel?.art || c.mangel?.zusammenfassung || '—'}
                    </span>
                    <div className="mt-1 inline-flex items-center gap-1 bg-secondary-container/30 text-on-secondary-container border border-secondary-container/50 px-2 py-0.5 rounded text-[11px] font-medium">
                      <span className="material-symbols-outlined text-[12px]">
                        category
                      </span>
                      {c.category}
                    </div>
                  </td>
                  <td className="py-4 px-4 max-w-xs">
                    <div className="mb-1">
                      <UrgencyBadge triage={c.triage} pending={c.triage_pending} />
                    </div>
                    {c.triage?.summary && (
                      <p className="text-[12px] text-on-surface-variant line-clamp-2">
                        {c.triage.summary}
                      </p>
                    )}
                  </td>
                  <td className="py-4 px-4 text-on-surface-variant">
                    {c.relative_time}
                  </td>
                  <td className="py-4 px-4 text-right">
                    <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        title="Details"
                        onClick={(e) => {
                          e.stopPropagation()
                          navigate(`/vorgang/${c.id}`)
                        }}
                        className="p-1.5 text-on-surface-variant hover:text-primary-container hover:bg-primary-container/10 rounded-md transition-colors"
                      >
                        <span className="material-symbols-outlined text-[20px]">
                          visibility
                        </span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, icon, accent }) {
  return (
    <div className="col-span-12 md:col-span-4 bg-surface-container-lowest border border-outline-variant/50 rounded-xl p-md shadow-sm flex flex-col justify-between">
      <div className="flex justify-between items-start mb-4">
        <span className="text-label-sm text-on-surface-variant uppercase tracking-wider">
          {label}
        </span>
        <span
          className={`material-symbols-outlined p-2 rounded-lg ${
            accent === 'error'
              ? 'text-error bg-error/10'
              : 'text-primary-container bg-primary-container/10'
          }`}
        >
          {icon}
        </span>
      </div>
      <div>
        <span className="text-h1 text-on-surface block">{value}</span>
      </div>
    </div>
  )
}

function CriticalAlert({ critical, onClick }) {
  return (
    <div
      onClick={onClick}
      className={`col-span-12 md:col-span-4 bg-gradient-to-br from-primary-container to-primary border border-primary/20 rounded-xl p-md shadow-sm text-white flex flex-col justify-between relative overflow-hidden ${
        critical ? 'cursor-pointer hover:shadow-lg transition-shadow' : ''
      }`}
    >
      <div className="absolute -right-6 -top-6 opacity-10">
        <span className="material-symbols-outlined text-[120px]">warning</span>
      </div>
      <div className="relative z-10 flex justify-between items-start mb-4">
        <span className="text-label-sm text-primary-fixed-dim uppercase tracking-wider">
          KI-Top-Empfehlung
        </span>
        <span className="bg-error text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
          {critical ? '1' : '0'}
        </span>
      </div>
      <div className="relative z-10">
        {critical ? (
          <>
            <p className="text-h3 font-semibold truncate mb-1">
              {critical.tenant?.adresse}
            </p>
            <p className="text-body-sm text-primary-fixed-dim line-clamp-3">
              {critical.triage?.summary || critical.triage?.urgency_reason || 'Sofortige Aktion erforderlich.'}
            </p>
          </>
        ) : (
          <p className="text-body-sm text-primary-fixed-dim">
            Aktuell keine kritischen Vorgänge.
          </p>
        )}
      </div>
    </div>
  )
}
