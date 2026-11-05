import { useCallback, useEffect, useState } from "react";
import { CircleCheck, RefreshCw, RotateCcw, X } from "lucide-react";
import { getAuditTrail, getReviewQueue, rejectRun, retryRun } from "../api/review.js";
import "./models.css";

const ACTION_LABELS = {
  "skill.promoted": "Promoted",
  "skill.retired": "Retired",
  "skill.restored": "Restored",
  "skill.imported": "Imported",
  "run.retried": "Retried",
  "run.rejected": "Rejected",
};

// Who changed what the registry trusts, and why (newest first).
function AuditTrail({ events }) {
  if (!events) return null;
  return (
    <section className="sf-audit" aria-labelledby="sf-audit-title">
      <h2 id="sf-audit-title">Audit trail</h2>
      {!events.length && <p className="sf-models__empty">No promotions, rollbacks or review decisions yet.</p>}
      {events.length > 0 && (
        <ol>
          {events.map((event) => (
            <li key={event.id}>
              <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time>
              <span className="sf-audit__action" data-action={event.action}>{ACTION_LABELS[event.action] || event.action}</span>
              <code>{event.target}</code>
              <span className="sf-audit__actor">by {event.actor}</span>
              <p>{event.reason}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export default function ReviewView({ onOpenRun }) {
  const [runs, setRuns] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [audit, setAudit] = useState(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const [queue, events] = await Promise.all([getReviewQueue(), getAuditTrail()]);
      setRuns(queue.runs);
      setAudit(events);
    } catch (failure) {
      setError(failure.message);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function act(run, action) {
    setBusy(run.execution_id);
    setNotice("");
    try {
      if (action === "retry") {
        const result = await retryRun(run.execution_id, 2);
        setNotice(`Queued again with a repair budget of ${result.repair_budget}. The worker will pick it up.`);
      } else {
        await rejectRun(run.execution_id);
        setNotice("Rejected. The run is marked failed.");
      }
      await load();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <section className="sf-models" aria-labelledby="sf-review-title">
      <header className="sf-models__header">
        <div>
          <p className="sf-models__label"><i />Human review</p>
          <h1 id="sf-review-title">Runs waiting for you</h1>
          <p className="sf-models__lead">When automatic repair runs out of budget, a run waits here instead of failing.
            <strong> Retry</strong> gives it a bigger repair budget; <strong>Reject</strong> closes it. To roll a skill back,
            retire its newest version in the Skill library.</p>
        </div>
        <button className="sf-models__refresh" onClick={load}><RefreshCw size={14} /> Refresh</button>
      </header>
      {error && <p className="sf-models__error" role="alert">{error}</p>}
      {notice && <p className="sf-models__empty" role="status">{notice}</p>}
      {runs && !runs.length && <p className="sf-models__empty"><CircleCheck size={14} /> Nothing to review. Every run either succeeded or was repaired automatically.</p>}

      <div className="sf-models__grid">
        {(runs || []).map((run) => (
          <article key={run.execution_id} className="sf-models__card" data-available="true">
            <div className="sf-models__card-top">
              <h2>{run.skill ? `${run.skill.id} v${run.skill.version}` : "Run"}</h2>
              <span className="sf-models__status"><i />{run.stage}</span>
            </div>
            <p className="sf-models__lead">{run.requirement}</p>
            <dl>
              <div><dt>Diagnosis</dt><dd><code>{run.failure?.code || "—"}</code></dd></div>
              <div><dt>Message</dt><dd>{run.failure?.message || "—"}</dd></div>
              <div><dt>Attempts</dt><dd>{run.attempts.length ? run.attempts.map((a) => a.strategy).join(", ") : "none"}</dd></div>
              <div><dt>Repair budget</dt><dd>{run.repair_budget ?? "default"}</dd></div>
            </dl>
            <div className="sf-review__actions">
              <button className="sf-models__refresh" disabled={busy === run.execution_id} onClick={() => act(run, "retry")}><RotateCcw size={14} /> Retry with +2 budget</button>
              <button className="sf-models__refresh" disabled={busy === run.execution_id} onClick={() => act(run, "reject")}><X size={14} /> Reject</button>
              {onOpenRun && <button className="sf-models__refresh" onClick={() => onOpenRun(run.execution_id)}>Open run</button>}
            </div>
          </article>
        ))}
      </div>

      <AuditTrail events={audit} />
    </section>
  );
}
