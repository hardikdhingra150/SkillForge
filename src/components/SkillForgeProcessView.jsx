import {
  useEffect,
  useId,
  useRef,
  useState,
} from "react";

import ExecutionHistory from "./ExecutionHistory.jsx";
import CSVInputPanel from "./CSVInputPanel.jsx";
import { TaskResult } from "./TaskResult.jsx";

import {
  useSkillForgeProcess,
} from "../hooks/useSkillForgeProcess.js";

import { submitClarification } from "../api/skillforgeProcess.js";

import "./skillforge-process-view.css";

function ClarifyForm({ executionId, question, onSent }) {
  const [answer, setAnswer] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  async function send(event) {
    event.preventDefault();
    if (!answer.trim()) return;
    setSending(true);
    setError("");
    try {
      await submitClarification(executionId, answer.trim());
      setAnswer("");
      onSent?.();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setSending(false);
    }
  }
  return (
    <form className="sf-process__clarify" onSubmit={send}>
      <p className="sf-process__eyebrow">The reviewer has a question</p>
      <p className="sf-process__question">{question}</p>
      <div className="sf-process__actions">
        <input value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Your answer…"
               aria-label="Answer the reviewer's question" maxLength={2000} />
        <button type="submit" disabled={sending || !answer.trim()}>{sending ? "Sending…" : "Send answer"}</button>
      </div>
      {error && <p className="sf-process__muted" role="alert">{error}</p>}
    </form>
  );
}

function readable(value) {
  return value.replaceAll("_", " ");
}

function time(value) {
  return new Date(value).toLocaleString();
}

export default function SkillForgeProcessView({
  requestedExecutionId = "",
  onOpenRequestHandled,
  onChanged,
}) {
  const process = useSkillForgeProcess();
  const runStatus = process.execution?.status;

  // Let the workspace numbers and lists catch up whenever this run moves on.
  useEffect(() => {
    if (runStatus) {
      onChanged?.();
    }
  }, [runStatus, onChanged]);
  const lastInputRequest = [...(process.events || [])].reverse().find((event) => event.event_type === "input_required");
  const clarifyQuestion = lastInputRequest?.payload?.next_action === "clarify_requirement"
    ? (lastInputRequest.payload.question || lastInputRequest.message) : "";

  const [draft, setDraft] = useState("");
  const [restoreId, setRestoreId] = useState("");

  const uid = useId();
  const panelRef = useRef(null);

  const requirement = (
    process.pending?.requirement ?? draft
  );

  const { openExecution } = process;

  useEffect(() => {
    if (!requestedExecutionId) {
      return;
    }

    openExecution(requestedExecutionId);
    onOpenRequestHandled?.("");

    panelRef.current?.scrollIntoView?.({
      block: "start",
      behavior: "auto",
    });
  }, [
    requestedExecutionId,
    openExecution,
    onOpenRequestHandled,
  ]);

  return (
    <section
      ref={panelRef}
      className="sf-process"
      aria-labelledby={`${uid}-title`}
    >
      <header className="sf-process__header">
        <div>
          <p className="sf-process__eyebrow">
            New task
          </p>

          <h2 id={`${uid}-title`}>
            Start a task
          </h2>

          <p>
            Describe what you need. SkillForge checks the request,
            asks for the file it needs, then shows every step here.
          </p>
        </div>
      </header>

      {process.error && (
        <div
          className="sf-process__error"
          role="alert"
        >
          {process.error}
        </div>
      )}

      <form
        onSubmit={(event) => {
          event.preventDefault();
          process.submit(requirement);
        }}
      >
        <label htmlFor={`${uid}-requirement`}>
          What would you like to do?
        </label>

        <textarea
          id={`${uid}-requirement`}
          placeholder="Show revenue by product from my sales data."
          value={requirement}
          onChange={(event) => {
            setDraft(event.target.value);
          }}
          minLength={5}
          maxLength={10000}
          required
          readOnly={
            Boolean(process.pending)
            || process.submitting
          }
          aria-describedby={`${uid}-scope`}
          rows={4}
        />

        <p
          id={`${uid}-scope`}
          className="sf-process__muted"
        >
          Be specific about the result you want. Example: “Total revenue
          per product from my sales export.” Today SkillForge works on CSV files.
        </p>

        {process.pending && (
          <p className="sf-process__notice">
            A submission is pending confirmation.
            Retry keeps the same submission key.
          </p>
        )}

        <div className="sf-process__actions">
          <button
            type="submit"
            disabled={
              process.submitting
              || Boolean(process.executionId)
            }
          >
            {process.submitting
              ? "Starting…"
              : process.pending
                ? "Retry"
                : "Start task"}
          </button>

          <button
            type="button"
            className="sf-process__secondary"
            disabled={process.submitting}
            onClick={() => {
              process.newTask();
              setDraft("");
            }}
          >
            New task
          </button>
        </div>

        <p className="sf-process__muted">
          New task clears this form. Earlier runs stay in Activity.
        </p>
      </form>

      <ExecutionHistory
        compact
        onOpen={process.openExecution}
        disabled={
          process.submitting
          || Boolean(process.pending)
        }
      />

      <details>
        <summary>
          Open using a task run ID
        </summary>

        <form
          className="sf-process__restore"
          onSubmit={(event) => {
            event.preventDefault();
            process.openExecution(restoreId);
          }}
        >
          <label htmlFor={`${uid}-restore`}>
            Task run ID
          </label>

          <div className="sf-process__actions">
            <input
              id={`${uid}-restore`}
              type="text"
              required
              placeholder="Paste a task run ID"
              value={restoreId}
              onChange={(event) => {
                setRestoreId(event.target.value);
              }}
            />

            <button
              type="submit"
              className="sf-process__secondary"
              disabled={
                process.submitting
                || Boolean(process.pending)
              }
            >
              Open
            </button>
          </div>
        </form>
      </details>

      {process.executionId && (
        <div className="sf-process__execution">
          <div className="sf-process__header">
            <h3>Current task</h3>

            <button
              type="button"
              className="sf-process__secondary"
              onClick={process.refresh}
              disabled={process.loading}
            >
              Refresh history
            </button>
          </div>

          <p className="sf-process__muted">
            Task run ID
          </p>

          <code className="sf-process__id">
            {process.executionId}
          </code>

          {process.execution ? (
            <>
              <p className="sf-process__requirement">
                {process.execution.requirement}
              </p>

              <dl className="sf-process__facts">
                <div>
                  <dt>Status</dt>
                  <dd>
                    {readable(
                      process.execution.status,
                    )}
                  </dd>
                </div>

                <div>
                  <dt>Current stage</dt>
                  <dd>
                    {readable(
                      process.execution.current_stage,
                    )}
                  </dd>
                </div>

                <div>
                  <dt>Recorded events</dt>
                  <dd>
                    {process.events.length}
                  </dd>
                </div>
              </dl>

              {process.execution.status === "queued"
                && (
                  <p className="sf-process__notice">
                    {process.execution.current_stage
                      === "skill_discovery"
                      ? "Inputs confirmed. Queued for skill discovery."
                      : "Request saved and queued. Waiting for requirement review."}
                  </p>
                )}

              {process.execution.status === "waiting_approval" && (
                <p className="sf-process__notice">
                  Automatic repair could not fix this run within its budget.
                  A person needs to review the diagnosis in the history below.
                </p>
              )}

              {process.execution.status === "waiting_input" && clarifyQuestion && (
                <ClarifyForm executionId={process.executionId} question={clarifyQuestion} onSent={process.refresh} />
              )}

              {process.execution.status
                === "waiting_input"
                && !clarifyQuestion
                && (
                  <p className="sf-process__notice">
                    More input is required. See the
                    recorded process history below.
                  </p>
                )}
            </>
          ) : (
            <p>
              {process.loading
                ? "Loading execution…"
                : "Execution details are unavailable."}
            </p>
          )}

          {process.execution && (
            <CSVInputPanel
              key={process.executionId}
              execution={process.execution}
              events={process.events}
              onUpdated={process.refresh}
            />
          )}

          {process.execution?.status === "succeeded" && (
            <TaskResult result={process.execution.result} />
          )}

          <h3>Recorded process history</h3>

          <ol className="sf-process__timeline">
            {process.events.map((event) => (
              <li
                key={
                  `${event.execution_id}:${event.sequence}`
                }
              >
                <span
                  className="sf-process__sequence"
                  aria-hidden="true"
                >
                  {event.sequence}
                </span>

                <div>
                  <p className="sf-process__message">
                    {event.message}
                  </p>

                  <p className="sf-process__muted">
                    {readable(event.stage)}
                    {" · "}

                    <time dateTime={event.created_at}>
                      {time(event.created_at)}
                    </time>
                  </p>

                  {Object.keys(
                    event.payload || {},
                  ).length > 0 && (
                    <details>
                      <summary>
                        View recorded details
                      </summary>

                      <pre>
                        {JSON.stringify(
                          event.payload,
                          null,
                          2,
                        )}
                      </pre>
                    </details>
                  )}
                </div>
              </li>
            ))}
          </ol>

          {process.events.length === 0 && (
            <p>No process events loaded yet.</p>
          )}

          {process.execution?.plan != null && (
            <details>
              <summary>Execution plan</summary>

              <pre>
                {JSON.stringify(
                  process.execution.plan,
                  null,
                  2,
                )}
              </pre>
            </details>
          )}

          {process.execution?.result != null && (
            <details>
              <summary>Raw result (JSON)</summary>

              <pre>
                {JSON.stringify(
                  process.execution.result,
                  null,
                  2,
                )}
              </pre>
            </details>
          )}

          {process.lastSynced && (
            <p className="sf-process__muted">
              Last synced:{" "}
              {process.lastSynced.toLocaleTimeString()}
            </p>
          )}
        </div>
      )}
    </section>
  );
}