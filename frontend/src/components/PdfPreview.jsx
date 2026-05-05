import { useRef } from 'react'
import html2pdf from 'html2pdf.js'

export default function PdfPreview({ caseData, onClose }) {
  const pageRef = useRef(null)

  const filename = `Rahlfs_Vorgang_${caseData.id}.pdf`

  const handleDownload = () => {
    if (!pageRef.current) return
    html2pdf()
      .from(pageRef.current)
      .set({
        margin: 0,
        filename,
        image: { type: 'jpeg', quality: 0.95 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
      })
      .save()
  }

  const tenant = caseData.tenant || {}
  const mangel = caseData.mangel || {}
  const fotos = caseData.fotos || []
  const triage = caseData.triage
  const today = new Date().toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-inverse-surface/70 backdrop-blur-sm p-lg"
      onClick={onClose}
    >
      <div
        className="w-full max-w-4xl bg-surface-container rounded-xl shadow-2xl flex flex-col overflow-hidden max-h-[92vh]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center px-md py-sm bg-surface-container-lowest border-b border-outline-variant shadow-sm z-10">
          <div className="flex items-center gap-sm">
            <span className="material-symbols-outlined text-on-surface-variant">
              description
            </span>
            <h2 className="text-h3 text-on-surface">Dokumentenvorschau</h2>
          </div>
          <div className="flex gap-sm">
            <button
              onClick={handleDownload}
              className="px-md py-sm bg-primary text-on-primary text-label-md rounded-lg flex items-center gap-xs hover:opacity-90 transition-colors"
            >
              <span className="material-symbols-outlined text-[18px]">download</span>
              Als PDF speichern
            </button>
            <button
              onClick={onClose}
              className="p-sm text-on-surface-variant hover:bg-surface-variant rounded-full flex items-center transition-colors"
            >
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto bg-surface p-lg flex justify-center">
          <div
            ref={pageRef}
            className="bg-surface-container-lowest w-full max-w-3xl shadow-sm border border-outline-variant p-margin-desktop rounded-sm flex flex-col gap-lg"
          >
            <div className="border-b-2 border-primary pb-sm flex justify-between items-start">
              <div>
                <p className="text-label-sm text-outline uppercase tracking-wider mb-xs">
                  Schadensmeldung / Ticket
                </p>
                <h1 className="text-h2 text-primary">
                  Vorgang: {caseData.id} — {mangel.art || 'Mangel'}
                </h1>
              </div>
              <div className="text-right">
                <h2 className="text-h3 text-primary tracking-widest font-bold">
                  RAHLFS
                </h2>
                <p className="text-label-sm text-on-surface-variant">
                  Immobilienverwaltung
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-x-gutter gap-y-md">
              <Field label="Mieter / Melder">
                <p className="text-body-md text-on-surface font-medium">
                  {tenant.name || '—'}
                </p>
                <p className="text-body-sm text-on-surface-variant">
                  {tenant.telefon || '—'}
                </p>
              </Field>
              <Field label="Objekt / Adresse">
                <p className="text-body-md text-on-surface font-medium">
                  {tenant.adresse || '—'}
                </p>
                <p className="text-body-sm text-on-surface-variant capitalize">
                  {caseData.mietertyp || ''}
                </p>
              </Field>
              <Field label="Kategorie">
                <p className="text-body-md text-on-surface font-medium">
                  {caseData.category}
                </p>
              </Field>
              <Field label="Erfassungsdatum">
                <p className="text-body-md text-on-surface font-medium">
                  {formatDate(caseData.timestamp)}
                </p>
              </Field>
            </div>

            <div className="border border-outline-variant rounded p-md bg-surface-container-lowest">
              <h3 className="text-h3 text-primary mb-sm">Detailbeschreibung</h3>
              <p className="text-body-md text-on-surface">
                {mangel.zusammenfassung || mangel.art || '—'}
              </p>
              <div className="grid grid-cols-2 gap-x-gutter gap-y-sm mt-md text-body-sm">
                <KV k="Art" v={mangel.art} />
                <KV k="Ort" v={mangel.ort} />
                <KV k="Ausmaß" v={mangel.ausmass} />
                <KV k="Seit" v={mangel.seit} />
                <KV k="Ursache" v={mangel.ursache} />
              </div>
            </div>

            {triage && (
              <div className="border-l-4 border-primary bg-surface-container-low rounded-r p-md">
                <div className="flex items-center justify-between mb-sm">
                  <h3 className="text-h3 text-primary">KI-Empfehlung für den Verwalter</h3>
                  <span className="px-2 py-1 rounded text-label-sm font-medium bg-primary text-on-primary capitalize">
                    {triage.urgency}
                  </span>
                </div>
                {triage.summary && (
                  <p className="text-body-md text-on-surface mb-sm font-medium">
                    {triage.summary}
                  </p>
                )}
                {triage.urgency_reason && (
                  <p className="text-body-sm text-on-surface-variant mb-md italic">
                    {triage.urgency_reason}
                  </p>
                )}
                {Array.isArray(triage.actions) && triage.actions.length > 0 && (
                  <div>
                    <p className="text-label-sm text-on-surface-variant uppercase tracking-wider mb-2">
                      Empfohlene Schritte
                    </p>
                    <ol className="list-decimal list-inside flex flex-col gap-1 text-body-md text-on-surface">
                      {triage.actions.map((a, i) => (
                        <li key={i}>
                          {a.label}
                          {a.deadline && (
                            <span className="ml-2 text-label-sm text-on-surface-variant">
                              ({a.deadline})
                            </span>
                          )}
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            )}

            {fotos.length > 0 && (
              <div>
                <p className="text-label-sm text-on-surface-variant mb-xs">
                  Fotodokumentation ({fotos.length})
                </p>
                <div className="grid grid-cols-2 gap-gutter">
                  {fotos.map((src, i) => (
                    <div
                      key={i}
                      className="border border-outline-variant rounded bg-surface-variant p-1 h-48 overflow-hidden"
                    >
                      <img
                        src={src}
                        alt={`Foto ${i + 1}`}
                        className="w-full h-full object-cover rounded-sm"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex-grow" />

            <div className="border-t border-outline-variant pt-sm mt-xl text-center">
              <p className="text-label-sm text-outline">
                Automatisch generiert über Rahlfs Assistant — {today}
              </p>
              <p className="text-label-sm text-outline mt-xs">Seite 1 von 1</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div className="bg-surface-container-low p-sm rounded border border-outline-variant">
      <p className="text-label-sm text-on-surface-variant mb-xs">{label}</p>
      {children}
    </div>
  )
}

function KV({ k, v }) {
  if (!v) return null
  return (
    <div>
      <span className="text-on-surface-variant">{k}: </span>
      <span className="text-on-surface">{v}</span>
    </div>
  )
}

function formatDate(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }) + ' Uhr'
  } catch {
    return iso
  }
}
