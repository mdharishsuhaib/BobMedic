// IncidentDetail.jsx — the diagnosis, the evidence, the diff, and the decision.

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
  diagnosing: 'Diagnosing',
}

const ACTION_LABEL = {
  auto_applied: 'Applied automatically',
  await_approval: 'Waiting for approval',
  escalated_no_fix: 'Escalated — no verified fix',
  blocked_risk_tier: 'Blocked by risk tier',
}

const SIGNAL_ORDER = ['text', 'attrs', 'dom_path', 'geometry', 'tag']
const SIGNAL_SHORT = { text: 'TXT', attrs: 'ATT', dom_path: 'DOM', geometry: 'POS', tag: 'TAG' }

function formatTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

export function Badge({ kind, children }) {
  return <span className={`badge ${kind}`}>{children}</span>
}

function ConfidenceBand({ confidence, thresholds }) {
  const ambiguous = thresholds?.ambiguous ?? 0.55
  const confident = thresholds?.confident ?? 0.85
  const percent = Math.max(0, Math.min(1, confidence || 0)) * 100

  return (
    <div className="band">
      <div className="band-track">
        <div className="band-needle" style={{ left: `${percent}%` }} />
      </div>
      <div className="band-scale">
        <span>0 · escalate</span>
        <span>{ambiguous} · ask Bob</span>
        <span>{confident} · auto</span>
        <span>1.0</span>
      </div>
    </div>
  )
}

function Candidates({ candidates, winnerText }) {
  if (!candidates?.length) return <div className="hint">No candidates were scored.</div>

  return (
    <table className="candidates">
      <thead>
        <tr>
          <th>Element</th>
          <th>Signals</th>
          <th style={{ textAlign: 'right' }}>Score</th>
        </tr>
      </thead>
      <tbody>
        {candidates.map((candidate, index) => {
          const isWinner = index === 0 && winnerText
          return (
            <tr key={index} className={isWinner ? 'winner' : ''}>
              <td>
                <div>
                  &lt;{candidate.tag}&gt; {candidate.text ? `"${candidate.text}"` : <em>no text</em>}
                </div>
                <div className="el">{candidate.dom_path}</div>
              </td>
              <td>
                <div className="signals">
                  {SIGNAL_ORDER.map((name) => (
                    <div className="signal" key={name} title={`${name}: ${candidate.signals?.[name] ?? 0}`}>
                      <div className="bar">
                        <i style={{ width: `${(candidate.signals?.[name] ?? 0) * 100}%` }} />
                      </div>
                      <div className="nm">{SIGNAL_SHORT[name]}</div>
                    </div>
                  ))}
                </div>
              </td>
              <td className="score" style={{ textAlign: 'right' }}>
                {candidate.score?.toFixed(2)}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function Diff({ diff }) {
  if (!diff?.length) return null
  return (
    <div className="diff">
      {diff.map((change, index) => (
        <div key={index}>
          <div className="diff-line removed">
            <span className="gut">− {change.line_number}</span>
            <span>{change.original}</span>
          </div>
          <div className="diff-line added">
            <span className="gut">+ {change.line_number}</span>
            <span>{change.patched}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function IncidentDetail({
  incident, thresholds, onApprove, onReject, busy, error,
}) {
  if (!incident) {
    return (
      <div className="panel detail">
        <div className="empty">Select an incident to see the diagnosis.</div>
      </div>
    )
  }

  const blocked = incident.action === 'blocked_risk_tier'
  const canDecide = incident.status === 'awaiting_approval' && incident.verified

  return (
    <div className="panel detail">
      <div className="detail-head">
        <div>
          <h2>{incident.bot_name}</h2>
          <div className="sub">
            {incident.id} · {incident.wal_file} · detected {formatTime(incident.detected_at)}
          </div>
        </div>
        <div className="badges">
          <Badge kind={incident.risk_tier}>{RISK_LABEL[incident.risk_tier]}</Badge>
          <Badge kind={incident.status}>{STATUS_LABEL[incident.status] || incident.status}</Badge>
        </div>
      </div>

      <div className="section">
        <h3>Failure</h3>
        <div className="kv-grid">
          <div className="kv">
            <div className="k">Error</div>
            <div className="v">{incident.error}</div>
          </div>
          <div className="kv">
            <div className="k">Failed step</div>
            <div className="v mono">{incident.failed_step}</div>
          </div>
          <div className="kv">
            <div className="k">Script line</div>
            <div className="v mono">{incident.wal_file}:{incident.script_line}</div>
          </div>
          <div className="kv">
            <div className="k">Page snapshot</div>
            <div className="v mono">{incident.page_html_ref}</div>
          </div>
        </div>
      </div>

      <div className="section">
        <h3>Diagnosis</h3>
        <p className="prose">{incident.diagnosis}</p>
        <div className="kv-grid" style={{ marginTop: 16 }}>
          <div className="kv">
            <div className="k">Confidence</div>
            <div className="v">{incident.confidence ? incident.confidence.toFixed(2) : '—'}</div>
          </div>
          <div className="kv">
            <div className="k">Resolved by</div>
            <div className="v">
              {incident.resolved_by === 'bob' ? 'Bob (semantic)'
                : incident.resolved_by === 'deterministic' ? 'Deterministic scoring'
                : 'Not resolved'}
            </div>
          </div>
          <div className="kv">
            <div className="k">Verified by re-run</div>
            <div className="v" style={{ color: incident.verified ? 'var(--green)' : 'var(--red)' }}>
              {incident.verified ? 'Yes' : 'No'}
            </div>
          </div>
          <div className="kv">
            <div className="k">Outcome</div>
            <div className="v">{ACTION_LABEL[incident.action] || incident.action}</div>
          </div>
        </div>
        <div style={{ marginTop: 16 }}>
          <ConfidenceBand confidence={incident.confidence} thresholds={thresholds} />
        </div>
      </div>

      {blocked && (
        <div className="section">
          <div className="refusal">
            <div className="title">Self-healing refused — irreversible bot</div>
            <p>
              BotMedic diagnosed this break and stopped there. This bot submits a payment,
              so a patch is never written, verified, or applied automatically, however
              confident the match is. An operator has to make the change by hand.
            </p>
            {incident.withheld_candidate && (
              <div className="withheld">
                Withheld match: &lt;{incident.withheld_candidate.tag}&gt;{' '}
                "{incident.withheld_candidate.text}"{' '}
                id={incident.withheld_candidate.attrs?.id || '—'}{' '}
                (scored {incident.withheld_candidate.score?.toFixed(2)})
              </div>
            )}
          </div>
        </div>
      )}

      <div className="section">
        <h3>Candidates scored on the changed page</h3>
        <Candidates candidates={incident.candidates} winnerText={!!incident.new_selector} />
      </div>

      {incident.diff?.length > 0 && (
        <div className="section">
          <h3>Proposed change</h3>
          <Diff diff={incident.diff} />
          {incident.selector_basis && (
            <div className="basis">Patched against: {incident.selector_basis}</div>
          )}
          {incident.run_result && (
            <div className="basis">
              Verification re-run: {incident.run_result.steps_run} steps in{' '}
              {incident.run_result.duration_sec}s — {incident.run_result.success ? 'passed' : 'failed'}
            </div>
          )}
        </div>
      )}

      <div className="section">
        <h3>Decision</h3>
        {canDecide ? (
          <div className="actions">
            <button className="btn primary" disabled={busy}
                    onClick={() => onApprove(incident)}>
              {busy ? 'Re-running…' : 'Approve & rerun'}
            </button>
            <button className="btn danger" disabled={busy}
                    onClick={() => onReject(incident)}>
              Reject
            </button>
            <span className="hint">
              Approving writes the patch to {incident.wal_file} and re-runs the bot.
            </span>
          </div>
        ) : (
          <div className="hint">
            {incident.status === 'healed'
              ? 'Patch applied and the bot completed its run.'
              : incident.status === 'rejected'
              ? `Rejected: ${incident.reject_reason || 'no reason given'}`
              : blocked
              ? 'No action available — the risk tier blocks automated repair.'
              : 'No verified patch to approve. This incident needs a human.'}
          </div>
        )}
        {error && <div className="error-line">{error}</div>}
      </div>
    </div>
  )
}


