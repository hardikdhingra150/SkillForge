import { useId, useState } from "react";
import { useSkillForgeProcess } from "../hooks/useSkillForgeProcess.js";
import "./skillforge-process-view.css";

function readable(value) {
  return value.replaceAll("_", " ");
}

function time(value) {
  return new Date(value).toLocaleString();
}

export default function SkillForgeProcessView() {
  const process = useSkillForgeProcess();
  const [draft, setDraft] = useState("");
  const [restoreId, setRestoreId] = useState("");
  const uid = useId();
  const requirement = process.pending?.requirement ?? draft;

  return (
    <section className="sf-process" aria-labelledby={`${uid}-title`}>
      <header className="sf-process__header">
        <div>
          <p className="sf-process__eyebrow">SkillForge workbench</p>
          <h2 id={`${uid}-title`}>Process View</h2>
          <p>Submit a requirement and follow its recorded progress.</p>
        </div>
        <span className="sf-process__badge">API mode</span>
      </header>

      {process.error && (
        <div className="sf-process__error" role="alert">{process.error}</div>
      )}

      <form onSubmit={(event) => {
        event.preventDefault();
        process.submit(requirement);
      }}>
        <label htmlFor={`${uid}-requirement`}>What would you like to do?</label>
        <textarea
          id={`${uid}-requirement`}
          placeholder="Show revenue by product from my sales data."
          value={requirement}
          onChange={(event) => setDraft(event.target.value)}
          minLength={5}
          maxLength={10000}
          required
          readOnly={Boolean(process.pending) || process.submitting}
          aria-describedby={`${uid}-scope`}
          rows={4}
        />
        <p id={`${uid}-scope`} className="sf-process__muted">
          This step saves the request and its history. File uploads and skill execution come next.
        </p>
        {process.pending && (
          <p className="sf-process__notice">
            A submission is pending confirmation. Retry keeps the same submission key.
          </p>
        )}
        <div className="sf-process__actions">
          <button type="submit" disabled={process.submitting || Boolean(process.executionId)}>
            {process.submitting ? "Saving request…" : process.pending ? "Retry submission" : "Submit requirement"}
          </button>
          <button type="button" className="sf-process__secondary"
            disabled={process.submitting}
            onClick={() => {
              process.newTask();
              setDraft("");
            }}>
            New task
          </button>
        </div>
        <p className="sf-process__muted">New task clears this view; saved backend executions remain available.</p>
      </form>

      <form className="sf-process__restore" onSubmit={(event) => {
        event.preventDefault();
        process.openExecution(restoreId);
      }}>
        <label htmlFor={`${uid}-restore`}>Open a saved execution</label>
        <div className="sf-process__actions">
          <input id={`${uid}-restore`} type="text" required
            placeholder="Paste the execution_id from Swagger"
            value={restoreId} onChange={(event) => setRestoreId(event.target.value)} />
          <button type="submit" className="sf-process__secondary"
            disabled={process.submitting || Boolean(process.pending)}>Open</button>
        </div>
      </form>

      {process.executionId && (
        <div className="sf-process__execution">
          <div className="sf-process__header">
            <h3>Current execution</h3>
            <button type="button" className="sf-process__secondary"
              onClick={process.refresh} disabled={process.loading}>Refresh history</button>
          </div>
          <p className="sf-process__muted">Execution ID</p>
          <code className="sf-process__id">{process.executionId}</code>
          {process.execution ? (
            <>
              <p className="sf-process__requirement">{process.execution.requirement}</p>
              <dl className="sf-process__facts">
                <div><dt>Status</dt><dd>{readable(process.execution.status)}</dd></div>
                <div><dt>Current stage</dt><dd>{readable(process.execution.current_stage)}</dd></div>
                <div><dt>Recorded events</dt><dd>{process.events.length}</dd></div>
              </dl>
              {process.execution.status === "queued" && (
  <p className="sf-process__notice">
    Request saved and queued.
    Waiting for a worker to start processing.
  </p>
)}

{process.execution.status === "waiting_input" && (
  <p className="sf-process__notice">
    More input is required.
    See the recorded process history below.
  </p>
)}
            </>
          ) : <p>{process.loading ? "Loading execution…" : "Execution details are unavailable."}</p>}

          <h3>Recorded process history</h3>
          <ol className="sf-process__timeline">
            {process.events.map((event) => (
              <li key={`${event.execution_id}:${event.sequence}`}>
                <span className="sf-process__sequence" aria-hidden="true">{event.sequence}</span>
                <div>
                  <p className="sf-process__message">{event.message}</p>
                  <p className="sf-process__muted">
                    {readable(event.stage)} · <time dateTime={event.created_at}>{time(event.created_at)}</time>
                  </p>
                  {Object.keys(event.payload || {}).length > 0 && (
                    <details>
                      <summary>View recorded details</summary>
                      <pre>{JSON.stringify(event.payload, null, 2)}</pre>
                    </details>
                  )}
                </div>
              </li>
            ))}
          </ol>
          {process.events.length === 0 && <p>No process events loaded yet.</p>}
          {process.execution?.plan != null && (
            <details><summary>Execution plan</summary><pre>{JSON.stringify(process.execution.plan, null, 2)}</pre></details>
          )}
          {process.execution?.result != null && (
            <details><summary>Result</summary><pre>{JSON.stringify(process.execution.result, null, 2)}</pre></details>
          )}
          {process.lastSynced && (
            <p className="sf-process__muted">Last synced: {process.lastSynced.toLocaleTimeString()}</p>
          )}
        </div>
      )}
    </section>
  );
}
