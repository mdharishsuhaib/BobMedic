// App.jsx — BotMedic control centre.

import { useCallback, useEffect, useRef, useState } from 'react'

import IncidentDetail, { Badge } from './IncidentDetail.jsx'
import MttrGauge from './MttrGauge.jsx'
import {
  SOURCE, approveIncident, loadFeed, loadScenarios, loadStatus,
  rejectIncident, startRun,
} from './api.js'

const RISK_LABEL = {
  read_only: 'read only',
  reversible_write: 'reversible write',
  irreversible: 'irreversible',
}

const STATUS_LABEL = {
  healed: 'Healed',
  awaiting_approval: 'Awaiting approval',
  escalated: 'Escalated',
  rejected: 'Rejected',
}

const SOURCE_LABEL = {
  [SOURCE.LIVE]: 'Engine connected',
  [SOURCE.FILE]: 'Reading incidents.json',
  [SOURCE.MOCK]: 'Sample data',
}

function shortTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

function BotCard({ bot, scenarios, busy, onRun }) {
  const [scenario, setScenario] = useState(scenarios[0]?.id || '')

  return (
    <div className={`bot-card ${bot.risk_tier}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span className="name">{bot.bot_name}</span>
        <span style={{ marginLeft: 'auto' }}>
          <Badge kind={bot.risk_tier}>{RISK_LABEL[bot.risk_tier]}</Badge>
        </span>
      </div>
      <div className="desc">{bot.description}</div>
      <div className="wal">{bot.wal || bot.bot_id}</div>
      <div className="bot-actions">
        <select className="scenario" value={scenario} disabled={!scenarios.length}
                onChange={(event) => setScenario(event.target.value)}>
          {scenarios.length === 0 && <option>engine offline</option>}
          {scenarios.map((item) => (
            <option key={item.id} value={item.id}>{item.id}</option>
          ))}
        </select>
        <button className="btn small" disabled={busy || !scenarios.length}
                onClick={() => onRun(bot.bot_id, scenario)}>
          Break &amp; run
        </button>
      </div>
    </div>
  )
}

export default function App() {
  const [feed, setFeed] = useState(null)
  const [source, setSource] = useState(SOURCE.MOCK)
  const [scenarios, setScenarios] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [job, setJob] = useState({ running: false, label: null })
  const [error, setError] = useState(null)
  const selectedRef = useRef(null)

  const refresh = useCallback(async () => {
    const { feed: next, source: nextSource } = await loadFeed()
    setFeed(next)
    setSource(nextSource)
    setSelectedId((current) => current || next.incidents?.[0]?.id || null)
  }, [])

  useEffect(() => { refresh() }, [refresh])

  useEffect(() => {
    loadScenarios()
      .then((data) => setScenarios(data.scenarios || []))
      .catch(() => setScenarios([]))
  }, [])

  // While the engine is working, poll until it goes quiet, then reload.
  useEffect(() => {
    if (!job.running) return undefined
    const timer = setInterval(async () => {
      try {
        const status = await loadStatus()
        if (!status.running) {
          setJob({ running: false, label: null })
          if (status.error) setError(status.error)
          await refresh()
        }
      } catch {
        setJob({ running: false, label: null })
      }
    }, 1500)
    return () => clearInterval(timer)
  }, [job.running, refresh])

  const incidents = feed?.incidents || []
  const selected = incidents.find((item) => item.id === selectedId) || incidents[0] || null
  selectedRef.current = selected
  const summary = feed?.summary || {}

  async function handleRun(botId, scenario) {
    setError(null)
    try {
      const result = await startRun(botId, scenario)
      setJob({ running: true, label: result.label })
    } catch (runError) {
      setError(runError.message)
    }
  }

  async function handleApprove(incident) {
    setError(null)
    try {
      // The engine re-runs against the break state stored on the incident.
      await approveIncident(incident.id)
      setJob({ running: true, label: `approve ${incident.id}` })
    } catch (approveError) {
      setError(approveError.message)
    }
  }

  async function handleReject(incident) {
    setError(null)
    try {
      await rejectIncident(incident.id, 'Rejected by operator')
      await refresh()
    } catch (rejectError) {
      setError(rejectError.message)
    }
  }

  return (
    <div className="shell">
      <header className="app-header">
        <div className="mark">B</div>
        <div className="wordmark">
          BotMedic
          <span>Self-healing RPA maintenance · by Team BobVanta</span>
        </div>
        <div className="header-right">
          {job.running && (
            <span className="source-pill">
              <span className="dot busy" />
              Running {job.label}
            </span>
          )}
          <span className="source-pill">
            <span className={`dot ${source}`} />
            {SOURCE_LABEL[source]}
          </span>
          <button className="btn small" onClick={refresh}>Refresh</button>
        </div>
      </header>

      <div className="top-row">
        <MttrGauge
          manualMinutes={summary.avg_manual_min}
          autoSeconds={summary.avg_auto_sec}
        />

        <div className="stat-grid">
          <div className="panel stat">
            <div className="value green">{summary.healed ?? 0}</div>
            <div>
              <div className="label">Healed automatically</div>
              <div className="note">verified by a re-run before anyone saw it</div>
            </div>
          </div>
          <div className="panel stat">
            <div className="value amber">{summary.awaiting_approval ?? 0}</div>
            <div>
              <div className="label">Awaiting approval</div>
              <div className="note">patch ready, human decides</div>
            </div>
          </div>
          <div className="panel stat">
            <div className="value red">{summary.escalated ?? 0}</div>
            <div>
              <div className="label">Escalated</div>
              <div className="note">risk tier blocked, or no verified fix</div>
            </div>
          </div>
          <div className="panel stat">
            <div className="value violet">
              {summary.bob_calls ?? 0}<span style={{ fontSize: 16, color: 'var(--dim)' }}>
                /{summary.incidents ?? 0}</span>
            </div>
            <div>
              <div className="label">Bob calls</div>
              <div className="note">only the ambiguous band reaches a model</div>
            </div>
          </div>
        </div>
      </div>

      <div className="panel fleet">
        <div className="fleet-head">
          <div className="panel-title">Bot fleet</div>
          <span className="hint">
            Each bot carries a risk tier. It decides what BotMedic is allowed to do when the bot breaks.
          </span>
        </div>
        <div className="fleet-grid">
          {(feed?.bots || []).map((bot) => (
            <BotCard key={bot.bot_id} bot={bot} scenarios={scenarios}
                     busy={job.running} onRun={handleRun} />
          ))}
        </div>
      </div>

      <div className="main">
        <div className="panel incident-list">
          <div className="list-head">
            <div className="panel-title">Incidents</div>
            <span className="hint" style={{ marginLeft: 'auto' }}>{incidents.length}</span>
          </div>
          {incidents.length === 0 && (
            <div className="empty">No incidents yet. Break a bot above.</div>
          )}
          {incidents.map((incident) => (
            <button
              key={incident.id}
              className={`incident status-${incident.status} ${
                selected?.id === incident.id ? 'selected' : ''}`}
              onClick={() => setSelectedId(incident.id)}
            >
              <div className="top">
                <span className="run-id">{incident.id}</span>
                <span className="when" style={{ marginLeft: 'auto' }}>
                  {shortTime(incident.detected_at)}
                </span>
              </div>
              <div className="bot">{incident.bot_name}</div>
              <div className="meta">
                <Badge kind={incident.status}>
                  {STATUS_LABEL[incident.status] || incident.status}
                </Badge>
                <Badge kind={incident.risk_tier}>{RISK_LABEL[incident.risk_tier]}</Badge>
                {incident.resolved_by === 'bob' && <Badge kind="ghost">Bob</Badge>}
              </div>
            </button>
          ))}
        </div>

        <IncidentDetail
          incident={selected}
          thresholds={feed?.thresholds}
          onApprove={handleApprove}
          onReject={handleReject}
          busy={job.running}
          error={error}
        />
      </div>
    </div>
  )
}


