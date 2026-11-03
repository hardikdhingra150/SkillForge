import { useCallback, useEffect, useState } from "react";
import { CircleCheck, RefreshCw, RotateCcw, X } from "lucide-react";
import { getReviewQueue, rejectRun, retryRun } from "../api/review.js";
import "./models.css";

export default function ReviewView({ onOpenRun }) {
  const [runs, setRuns] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      setRuns((await getReviewQueue()).runs);
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
    </section>
  );
}
