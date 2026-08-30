// MttrGauge.jsx — mean time to repair, manual against automated.

const RADIUS = 74
const STROKE = 14
const SIZE = RADIUS * 2 + STROKE + 8

/** Point on the gauge arc at a fraction of the sweep (0 = left, 1 = right). */
function pointAt(fraction) {
  const angle = Math.PI * (1 - fraction)
  return {
    x: SIZE / 2 + RADIUS * Math.cos(angle),
    y: SIZE / 2 + 6 - RADIUS * Math.sin(angle),
  }
}

/** SVG path for a slice of the arc. */
function arcPath(fraction) {
  const start = pointAt(0)
  const end = pointAt(Math.max(0.001, Math.min(1, fraction)))
  const largeArc = fraction > 0.5 ? 1 : 0
  return `M ${start.x} ${start.y} A ${RADIUS} ${RADIUS} 0 ${largeArc} 1 ${end.x} ${end.y}`
}

/** Format seconds the way an operator reads them. */
function humanSeconds(seconds) {
  if (!seconds) return '—'
  if (seconds < 90) return `${Math.round(seconds)}s`
  return `${(seconds / 60).toFixed(1)} min`
}

export default function MttrGauge({ manualMinutes, autoSeconds }) {
  const manualSeconds = (manualMinutes || 0) * 60
  const hasData = manualSeconds > 0 && autoSeconds > 0
  const reduction = hasData ? Math.max(0, 1 - autoSeconds / manualSeconds) : 0
  const percent = Math.round(reduction * 100)

  return (
    <div className="panel mttr">
      <svg width={SIZE} height={SIZE / 2 + 24} role="img"
           aria-label={`Repair time reduced by ${percent} percent`}>
        <defs>
          <linearGradient id="mttr-fill" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#2dd4bf" />
            <stop offset="100%" stopColor="#34d399" />
          </linearGradient>
        </defs>

        <path d={arcPath(1)} fill="none" stroke="#1e2a42"
              strokeWidth={STROKE} strokeLinecap="round" />
        <path d={arcPath(reduction)} fill="none" stroke="url(#mttr-fill)"
              strokeWidth={STROKE} strokeLinecap="round" />

        <text x={SIZE / 2} y={SIZE / 2 - 12} textAnchor="middle"
              fill="#e6edf7" fontSize="30" fontWeight="700">
          {hasData ? `${percent}%` : '—'}
        </text>
        <text x={SIZE / 2} y={SIZE / 2 + 8} textAnchor="middle"
              fill="#8296b4" fontSize="11" letterSpacing="0.6">
          FASTER
        </text>
      </svg>

      <div className="mttr-figures">
        <div className="panel-title">Mean time to repair</div>
        <div className="mttr-headline">{hasData ? humanSeconds(autoSeconds) : 'No data'}</div>
        <div className="mttr-sub">
          Average time from a bot failing to a verified patch being ready for a human.
        </div>
        <div className="mttr-compare">
          <span className="before">{manualMinutes ? `${manualMinutes} min` : '—'}</span>
          <span className="unit">manual repair</span>
          <span className="arrow">→</span>
          <span className="after">{humanSeconds(autoSeconds)}</span>
          <span className="unit">BotMedic</span>
        </div>
      </div>
    </div>
  )
}


