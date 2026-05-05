import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { assignHandwerker, fetchCase, fetchHandwerker } from '../api'
import PdfPreview from '../components/PdfPreview'

const PRIORITY_LABEL = {
  emergency: 'Notfall',
  normal: 'Normal',
  low: 'Niedrig',
}

const PRIORITY_DOT = {
  emergency: 'bg-error',
  normal: 'bg-secondary',
  low: 'bg-outline',
}

const URGENCY_TONE = {
  kritisch: { bg: 'bg-error', text: 'text-on-error', soft: 'bg-error/10', softText: 'text-error', label: 'Kritisch — sofortige Aktion' },
  hoch: { bg: 'bg-error', text: 'text-on-error', soft: 'bg-error/10', softText: 'text-error', label: 'Hohe Dringlichkeit' },
  mittel: { bg: 'bg-secondary', text: 'text-on-secondary', soft: 'bg-secondary/15', softText: 'text-on-secondary-container', label: 'Mittlere Dringlichkeit' },
  niedrig: { bg: 'bg-outline-variant', text: 'text-on-surface', soft: 'bg-outline/10', softText: 'text-on-surface-variant', label: 'Niedrig' },
}

const DEADLINE_TONE = {
  sofort: 'bg-error/10 text-error border-error/30',
  '24h': 'bg-error/10 text-error border-error/20',
  'diese woche': 'bg-secondary/10 text-on-secondary-container border-secondary/30',
  'nächste woche': 'bg-outline/10 text-on-surface-variant border-outline/20',
}

export default function VorgangDetail() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [showPdf, setShowPdf] = useState(false)
  const [showHandwerker, setShowHandwerker] = useState(false)

  useEffect(() => {
    let active = true
    fetchCase(caseId)
      .then((d) => {
        if (active) {
          setData(d)
          setError(null)
        }
      })
      .catch((e) => {
        if (active) setError(e.message)
      })
    return () => {
      active = false
    }
  }, [caseId])

  if (error) {
    return (
      <div className="p-margin-desktop">
        <button
          onClick={() => navigate('/')}
          className="text-label-md text-on-surface-variant flex items-center gap-1 mb-md hover:text-primary-container"
        >
          <span className="material-symbols-outlined text-[18px]">arrow_back</span>
          Zurück zur Übersicht
        </button>
        <div className="bg-error-container text-on-error-container p-md rounded-lg">
          Fehler: {error}
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="p-margin-desktop text-on-surface-variant">Lädt…</div>
    )
  }

  const tenant = data.tenant || {}
  const mangel = data.mangel || {}
  const fotos = data.fotos || []
  const triage = data.triage
  const triagePending = data.triage_pending
  const initials = (tenant.name || '?')
    .split(' ')
    .map((n) => n[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <div className="p-margin-desktop">
      <button
        onClick={() => navigate('/')}
        className="text-label-md text-on-surface-variant flex items-center gap-1 mb-md hover:text-primary-container"
      >
        <span className="material-symbols-outlined text-[18px]">arrow_back</span>
        Zurück zur Übersicht
      </button>

      <div className="flex justify-between items-start mb-lg">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-label-sm text-on-surface-variant uppercase tracking-wider">
              Vorgang Detail
            </span>
            <span className="w-1 h-1 rounded-full bg-outline-variant" />
            <span className="text-label-sm text-on-surface-variant">
              Erstellt {data.relative_time}
            </span>
          </div>
          <h2 className="text-h1 text-on-surface">
            Vorgang {data.id} — {mangel.art || 'Mangelmeldung'}
          </h2>
        </div>
        <div className="flex gap-sm">
          <button
            onClick={() => setShowPdf(true)}
            className="bg-surface-container-lowest border border-outline-variant text-primary text-label-md px-4 py-2 rounded-lg hover:bg-surface-container transition-colors flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-[18px]">
              picture_as_pdf
            </span>
            PDF generieren
          </button>
          <button className="bg-surface-container-lowest border border-outline-variant text-primary text-label-md px-4 py-2 rounded-lg hover:bg-surface-container transition-colors flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">send</span>
            An Objektverantwortlichen senden
          </button>
          <button
            onClick={() => setShowHandwerker(true)}
            className="bg-primary text-on-primary text-label-md px-4 py-2 rounded-lg hover:opacity-90 transition-opacity flex items-center gap-2 shadow-sm"
          >
            <span className="material-symbols-outlined text-[18px]">engineering</span>
            {data.handwerker ? 'Handwerker neu zuweisen' : 'Handwerker zuweisen'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-gutter">
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-gutter">
          {data.handwerker && (
            <HandwerkerStatusCard handwerker={data.handwerker} termine={data.termine} />
          )}
          <TriageCard triage={triage} pending={triagePending} />

          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-md">
            <h3 className="text-h3 text-on-surface mb-md pb-sm border-b border-surface-variant flex items-center gap-2">
              <span className="material-symbols-outlined text-outline">info</span>
              Meldungsdetails
            </h3>
            <div className="grid grid-cols-2 gap-y-md gap-x-gutter mb-lg">
              <Field label="Mieter">
                <div className="text-body-md text-on-surface flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center text-[10px] font-medium">
                    {initials}
                  </div>
                  {tenant.name || '—'}
                </div>
              </Field>
              <Field label="Priorität">
                <div className="text-body-md text-on-surface flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${PRIORITY_DOT[data.priority]}`} />
                  {PRIORITY_LABEL[data.priority] || data.priority}
                </div>
              </Field>
              <Field label="Adresse">
                <div className="text-body-md text-on-surface">
                  {tenant.adresse || '—'}
                </div>
              </Field>
              <Field label="Telefon">
                <div className="text-body-md text-on-surface">
                  {tenant.telefon || '—'}
                </div>
              </Field>
              <Field label="Kategorie">
                <div className="text-body-md text-on-surface">{data.category}</div>
              </Field>
              <Field label="Mietertyp">
                <div className="text-body-md text-on-surface capitalize">
                  {data.mietertyp || '—'}
                </div>
              </Field>
              <Field label="Zeitpunkt der Feststellung">
                <div className="text-body-md text-on-surface">
                  {mangel.seit || '—'}
                </div>
              </Field>
              <Field label="Ursache">
                <div className="text-body-md text-on-surface">
                  {mangel.ursache || '—'}
                </div>
              </Field>
            </div>
            <div>
              <label className="block text-label-sm text-on-surface-variant mb-2">
                Beschreibung
              </label>
              <p className="text-body-md text-on-surface bg-surface p-sm rounded-lg border border-surface-variant">
                {mangel.zusammenfassung || mangel.art || '—'}
              </p>
            </div>
          </div>

          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-md">
            <div className="flex items-center justify-between mb-md pb-sm border-b border-surface-variant">
              <h3 className="text-h3 text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-outline">
                  smart_toy
                </span>
                KI-Erfassung (Telegram-Chat)
              </h3>
              <span className="bg-primary-fixed text-on-primary-fixed-variant text-[10px] px-2 py-1 rounded-full">
                Automatisch erfasst
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
              <KVRow k="Art" v={mangel.art} />
              <KVRow k="Ort" v={mangel.ort} />
              <KVRow k="Ausmaß" v={mangel.ausmass} />
              <KVRow k="Seit" v={mangel.seit} />
              <KVRow k="Ursache" v={mangel.ursache} />
            </div>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-4 flex flex-col gap-gutter">
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-md flex flex-col gap-4">
            <h3 className="text-label-md text-on-surface-variant flex items-center gap-2 uppercase tracking-wider">
              <span className="material-symbols-outlined text-[16px]">
                photo_camera
              </span>
              Anhang ({fotos.length})
            </h3>
            {fotos.length === 0 ? (
              <div className="text-body-sm text-on-surface-variant italic p-sm">
                Keine Fotos vorhanden.
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {fotos.map((src, i) => (
                  <a
                    key={i}
                    href={src}
                    target="_blank"
                    rel="noreferrer"
                    className="relative aspect-square rounded-lg overflow-hidden border border-outline-variant group"
                  >
                    <img
                      src={src}
                      alt={`Foto ${i + 1}`}
                      className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <span className="material-symbols-outlined text-white text-3xl drop-shadow-md">
                        zoom_in
                      </span>
                    </div>
                  </a>
                ))}
              </div>
            )}
          </div>

          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-md flex-1">
            <h3 className="text-label-md text-on-surface-variant flex items-center gap-2 uppercase tracking-wider mb-lg">
              <span className="material-symbols-outlined text-[16px]">history</span>
              Verlauf
            </h3>
            <div className="relative pl-3 border-l border-surface-variant flex flex-col gap-6">
              <LogItem
                title="KI-Erfassung abgeschlossen"
                desc="Daten strukturiert und Vorgang angelegt."
                ts={data.timestamp}
                primary
              />
              <LogItem
                title="Mangelmeldung gestartet"
                desc="Eingang via Telegram-Chatbot."
                ts={data.timestamp}
              />
            </div>
          </div>
        </div>
      </div>

      {showPdf && <PdfPreview caseData={data} onClose={() => setShowPdf(false)} />}
      {showHandwerker && (
        <HandwerkerModal
          caseId={data.id}
          onClose={() => setShowHandwerker(false)}
          onAssigned={(updated) => {
            setData(updated)
            setShowHandwerker(false)
          }}
        />
      )}
    </div>
  )
}

function HandwerkerStatusCard({ handwerker, termine }) {
  const ausgewaehlt = termine?.ausgewaehlt
  const vorgeschlagen = termine?.vorgeschlagen || []
  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-md">
      <div className="flex items-start justify-between mb-md pb-sm border-b border-surface-variant">
        <h3 className="text-h3 text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary-container">engineering</span>
          Zugewiesener Handwerker
        </h3>
        <span className="px-3 py-1 rounded-full text-label-sm font-medium bg-secondary/15 text-on-secondary-container border border-secondary/30 flex items-center gap-1">
          <span className="material-symbols-outlined text-[14px]">task_alt</span>
          Beauftragt
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-md mb-md">
        <div>
          <p className="text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">Betrieb</p>
          <p className="text-body-md text-on-surface font-medium">{handwerker.name}</p>
        </div>
        <div>
          <p className="text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">Gewerk</p>
          <p className="text-body-md text-on-surface">{handwerker.gewerk}</p>
        </div>
        <div>
          <p className="text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">Telefon</p>
          <p className="text-body-md text-on-surface">{handwerker.telefon}</p>
        </div>
        <div>
          <p className="text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">Beauftragt am</p>
          <p className="text-body-md text-on-surface">{formatTs(handwerker.assigned_at)}</p>
        </div>
      </div>
      <div>
        <p className="text-label-sm text-on-surface-variant uppercase tracking-wider mb-2">Terminwahl des Mieters</p>
        {ausgewaehlt ? (
          <div className="p-sm rounded-lg bg-secondary/10 text-on-secondary-container border border-secondary/30 flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">event_available</span>
            <span className="text-body-md font-medium">{ausgewaehlt.label}</span>
          </div>
        ) : (
          <div className="p-sm rounded-lg bg-surface-variant text-on-surface-variant border border-outline-variant/40 flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px] animate-pulse">hourglass_top</span>
            <span className="text-body-sm">
              {vorgeschlagen.length} Termine wurden dem Mieter via Telegram gesendet — wartet auf Auswahl.
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

function HandwerkerModal({ caseId, onClose, onAssigned }) {
  const [items, setItems] = useState(null)
  const [category, setCategory] = useState('')
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let active = true
    fetchHandwerker(caseId)
      .then((d) => {
        if (!active) return
        setItems(d.recommendations || [])
        setCategory(d.category || '')
      })
      .catch((e) => {
        if (active) setError(e.message)
      })
    return () => {
      active = false
    }
  }, [caseId])

  async function handleAssign() {
    if (!selected || submitting) return
    setSubmitting(true)
    try {
      const updated = await assignHandwerker(caseId, selected)
      onAssigned(updated)
    } catch (e) {
      setError(e.message)
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-md py-4 border-b border-outline-variant flex items-center justify-between">
          <div>
            <h3 className="text-h3 text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-primary-container">engineering</span>
              Empfohlene Handwerker
            </h3>
            <p className="text-label-sm text-on-surface-variant mt-1">
              Kategorie: <span className="font-medium">{category || '—'}</span> · Sortiert nach Bewertung & Entfernung
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface p-1 rounded"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-md">
          {error && (
            <div className="bg-error-container text-on-error-container p-sm rounded-lg mb-md">
              {error}
            </div>
          )}
          {!items && !error && (
            <div className="text-on-surface-variant flex items-center gap-2">
              <span className="material-symbols-outlined animate-spin">progress_activity</span>
              Lade Empfehlungen…
            </div>
          )}
          {items && items.length === 0 && (
            <div className="text-on-surface-variant italic">Keine Handwerker verfügbar.</div>
          )}
          {items && items.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {items.map((h) => {
                const isSelected = selected === h.id
                const isMatch = h.gewerk === category
                return (
                  <button
                    key={h.id}
                    onClick={() => setSelected(h.id)}
                    className={`text-left p-md rounded-lg border transition-all ${
                      isSelected
                        ? 'border-primary bg-primary/5 shadow-sm'
                        : 'border-outline-variant bg-surface hover:border-primary/50'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="text-body-md font-medium text-on-surface">{h.name}</p>
                        <p className="text-label-sm text-on-surface-variant">{h.gewerk}</p>
                      </div>
                      {isMatch && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-secondary/20 text-on-secondary-container border border-secondary/30 whitespace-nowrap">
                          Bestmatch
                        </span>
                      )}
                    </div>
                    <p className="text-body-sm text-on-surface-variant mb-2 line-clamp-2">
                      {h.beschreibung}
                    </p>
                    <div className="flex items-center gap-3 text-[12px] text-on-surface-variant">
                      <span className="flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px] text-amber-500">star</span>
                        {h.rating}
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px]">euro</span>
                        {h.stundensatz}/h
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px]">location_on</span>
                        {h.distance_km} km
                      </span>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        <div className="px-md py-4 border-t border-outline-variant flex items-center justify-between bg-surface-container-low">
          <p className="text-label-sm text-on-surface-variant">
            Nach der Auswahl erhält der Mieter automatisch 4 Terminvorschläge per Telegram.
          </p>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-outline-variant text-on-surface hover:bg-surface-container text-label-md"
            >
              Abbrechen
            </button>
            <button
              onClick={handleAssign}
              disabled={!selected || submitting}
              className="px-4 py-2 rounded-lg bg-primary text-on-primary text-label-md flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90"
            >
              {submitting && (
                <span className="material-symbols-outlined animate-spin text-[18px]">progress_activity</span>
              )}
              Beauftragen & Termine senden
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function TriageCard({ triage, pending }) {
  if (pending || !triage) {
    return (
      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-md">
        <h3 className="text-h3 text-on-surface mb-md pb-sm border-b border-surface-variant flex items-center gap-2">
          <span className="material-symbols-outlined text-primary-container">auto_awesome</span>
          KI-Empfehlung
        </h3>
        <div className="flex items-center gap-3 text-on-surface-variant">
          <span className="material-symbols-outlined animate-spin">progress_activity</span>
          <span className="text-body-sm">
            Die KI analysiert den Vorgang und erstellt eine Dringlichkeitsbewertung sowie
            Handlungsempfehlungen…
          </span>
        </div>
      </div>
    )
  }

  const tone = URGENCY_TONE[(triage.urgency || '').toLowerCase()] || URGENCY_TONE.niedrig

  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-md">
      <div className="flex items-start justify-between mb-md pb-sm border-b border-surface-variant">
        <h3 className="text-h3 text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary-container">auto_awesome</span>
          KI-Empfehlung
        </h3>
        <span className={`px-3 py-1 rounded-full text-label-sm font-medium ${tone.bg} ${tone.text} flex items-center gap-1`}>
          <span className="material-symbols-outlined text-[14px]">priority_high</span>
          {tone.label}
        </span>
      </div>

      {triage.summary && (
        <div className={`p-sm rounded-lg ${tone.soft} ${tone.softText} text-body-md mb-md`}>
          {triage.summary}
        </div>
      )}

      {triage.urgency_reason && (
        <div className="mb-md">
          <p className="text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">
            Begründung der Dringlichkeit
          </p>
          <p className="text-body-md text-on-surface">{triage.urgency_reason}</p>
        </div>
      )}

      {Array.isArray(triage.actions) && triage.actions.length > 0 && (
        <div>
          <p className="text-label-sm text-on-surface-variant uppercase tracking-wider mb-2">
            Empfohlene nächste Schritte
          </p>
          <ul className="flex flex-col gap-2">
            {triage.actions.map((a, i) => {
              const deadlineKey = (a.deadline || '').toLowerCase()
              const deadlineCls = DEADLINE_TONE[deadlineKey] || 'bg-outline/10 text-on-surface-variant border-outline/20'
              return (
                <li
                  key={i}
                  className="flex items-start justify-between gap-md p-sm rounded-lg border border-outline-variant/50 bg-surface"
                >
                  <div className="flex items-start gap-2 flex-1 min-w-0">
                    <span className="material-symbols-outlined text-primary-container text-[18px] mt-0.5">
                      check_circle
                    </span>
                    <span className="text-body-md text-on-surface">{a.label}</span>
                  </div>
                  {a.deadline && (
                    <span className={`shrink-0 px-2 py-0.5 rounded text-[11px] font-medium border whitespace-nowrap ${deadlineCls}`}>
                      {a.deadline}
                    </span>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-label-sm text-on-surface-variant mb-1">
        {label}
      </label>
      {children}
    </div>
  )
}

function KVRow({ k, v }) {
  return (
    <div>
      <p className="text-label-sm text-on-surface-variant mb-1">{k}</p>
      <p className="text-body-md text-on-surface">{v || '—'}</p>
    </div>
  )
}

function LogItem({ title, desc, ts, primary }) {
  return (
    <div className="relative">
      <span
        className={`absolute -left-[17px] top-1 w-2.5 h-2.5 rounded-full border-2 border-surface-container-lowest ${
          primary ? 'bg-primary' : 'bg-surface-variant'
        }`}
      />
      <div className="pl-4">
        <div className="text-label-md text-on-surface">{title}</div>
        <div className="text-body-sm text-on-surface-variant mt-0.5">{desc}</div>
        <div className="text-[11px] text-outline mt-1">{formatTs(ts)}</div>
      </div>
    </div>
  )
}

function formatTs(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}
