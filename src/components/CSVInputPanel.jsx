import { useEffect, useId, useRef, useState } from "react";
import { CheckCircle2, FileSpreadsheet, Sparkles, UploadCloud } from "lucide-react";
import { confirmCSVMapping, getCSVInput, uploadCSVInput } from "../api/skillforgeProcess.js";

const ACCEPT = ".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

function startingColumns(value) {
  return value?.column_mapping || value?.suggested_mapping || {};
}

function isAccepted(file) {
  return /\.(csv|xlsx)$/i.test(file?.name || "");
}

/** Drop or pick a CSV/Excel file, check the preview, then confirm the suggested columns. */
export default function CSVInputPanel({ execution, events, onUpdated }) {
  const uid = useId();
  const [input, setInput] = useState(null);
  const [columns, setColumns] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef(null);
  const actionController = useRef(null);

  useEffect(() => () => actionController.current?.abort(), []);

  useEffect(() => {
    const controller = new AbortController();
    getCSVInput(execution.execution_id, controller.signal).then((value) => {
      if (controller.signal.aborted) return;
      setInput(value);
      setColumns(startingColumns(value));
      setError("");
    }).catch((failure) => {
      if (controller.signal.aborted) return;
      if (failure.status === 404) setInput(null);
      else setError(failure.message);
    });
    return () => controller.abort();
  }, [execution.execution_id, execution.current_stage]);

  const canUpload = execution.status === "waiting_input" && (
    execution.current_stage === "column_mapping" ||
    events.some((event) => event.event_type === "input_required" && event.payload?.next_action === "upload_csv")
  );

  async function perform(action) {
    if (busy) return;
    setBusy(true);
    setError("");
    const controller = new AbortController();
    actionController.current = controller;
    try {
      const value = await action(controller.signal);
      if (controller.signal.aborted) return;
      setInput(value);
      setColumns(startingColumns(value));
      onUpdated();
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure.message);
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  function upload(file) {
    if (!file) return;
    if (!isAccepted(file)) {
      setError("Choose a .csv or .xlsx file.");
      return;
    }
    perform((signal) => uploadCSVInput(execution.execution_id, file, signal));
  }

  if (!canUpload && !input && !error) return null;

  const workflow = input?.workflow;
  const roles = workflow?.roles || [];
  const suggested = input?.suggested_mapping || {};
  const chosen = Object.values(columns).filter(Boolean);
  const missing = roles.some((role) => role.required && !columns[role.name]);
  const repeated = new Set(chosen).size !== chosen.length;
  const label = (name) => roles.find((role) => role.name === name)?.label || name;

  return (
    <section className="sf-upload" aria-labelledby={`${uid}-title`}>
      <header className="sf-upload__head">
        <div>
          <p className="sf-process__eyebrow">Step 2 · Your file</p>
          <h3 id={`${uid}-title`}>{workflow ? workflow.title : "Upload your file"}</h3>
          {workflow?.about && <p className="sf-process__muted">{workflow.about}</p>}
        </div>
      </header>

      {error && <p role="alert" className="sf-process__error">{error}</p>}

      {canUpload && !input?.confirmed && (
        <div
          className={`sf-drop${dragging ? " is-dragging" : ""}${busy ? " is-busy" : ""}`}
          onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            upload(event.dataTransfer.files?.[0]);
          }}
        >
          <UploadCloud size={26} aria-hidden="true" />
          <p className="sf-drop__title">
            {busy ? "Reading your file…" : input ? "Drop a different file to replace it" : "Drop your CSV or Excel file here"}
          </p>
          <p className="sf-process__muted">.csv or .xlsx · first sheet · up to 10,000 rows</p>
          <input
            ref={fileRef}
            id={`${uid}-file`}
            className="sf-drop__input"
            type="file"
            accept={ACCEPT}
            disabled={busy}
            onChange={(event) => {
              upload(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
          <button type="button" className="sf-process__secondary" disabled={busy} onClick={() => fileRef.current?.click()}>
            <FileSpreadsheet size={15} aria-hidden="true" />
            {input ? "Choose another file" : "Choose a file"}
          </button>
        </div>
      )}

      {input && (
        <>
          <p className="sf-upload__file">
            <FileSpreadsheet size={15} aria-hidden="true" />
            <strong>{input.filename}</strong>
            <span>{input.row_count.toLocaleString()} rows · {input.headers.length} columns</span>
          </p>

          <div className="sf-upload__preview">
            <table>
              <caption>First {input.preview.length} rows</caption>
              <thead>
                <tr>{input.headers.map((header) => {
                  const role = Object.keys(columns).find((name) => columns[name] === header);
                  return <th key={header} className={role ? "is-mapped" : undefined}>
                    {header}{role && <small>{label(role)}</small>}
                  </th>;
                })}</tr>
              </thead>
              <tbody>{input.preview.map((row, index) => (
                <tr key={index}>{row.map((value, column) => <td key={column}>{value}</td>)}</tr>
              ))}</tbody>
            </table>
          </div>

          {input.confirmed ? (
            <p className="sf-process__notice sf-upload__done">
              <CheckCircle2 size={15} aria-hidden="true" />
              {roles.length && Object.keys(input.column_mapping || {}).length
                ? `Confirmed: ${Object.entries(input.column_mapping).map(([name, header]) => `${label(name).toLowerCase()} = ${header}`).join(" · ")}`
                : "Confirmed. No columns needed."}
            </p>
          ) : canUpload && (
            <form
              className="sf-upload__mapping"
              onSubmit={(event) => {
                event.preventDefault();
                perform((signal) => confirmCSVMapping(execution.execution_id, {
                  file_sha256: input.sha256, file_version: input.version, columns,
                }, signal));
              }}
            >
              {roles.length > 0 && Object.keys(suggested).length > 0 && (
                <p className="sf-upload__hint"><Sparkles size={14} aria-hidden="true" />
                  Columns suggested from the headers and values. Check them, then confirm.</p>
              )}
              {roles.length === 0 && <p className="sf-process__muted">This task works on the whole table. Nothing to choose.</p>}
              <div className="sf-upload__roles">
                {roles.map((role) => (
                  <label key={role.name}>
                    <span>{role.label}{!role.required && <em> (optional)</em>}
                      {suggested[role.name] && suggested[role.name] === columns[role.name] && <b className="sf-upload__tag">Suggested</b>}
                    </span>
                    <select
                      value={columns[role.name] || ""}
                      disabled={busy}
                      required={role.required}
                      onChange={(event) => setColumns({ ...columns, [role.name]: event.target.value })}
                    >
                      <option value="">{role.required ? "Choose a column" : "Whole row (no key)"}</option>
                      {input.headers.map((header) => <option key={header} value={header}>{header}</option>)}
                    </select>
                    {role.help && <small>{role.help}</small>}
                  </label>
                ))}
              </div>
              {repeated && <p className="sf-process__muted">Each column can only be used once.</p>}
              <button type="submit" disabled={busy || missing || repeated}>
                {busy ? "Confirming…" : roles.length ? "Confirm columns and run" : "Run it"}
              </button>
            </form>
          )}
        </>
      )}
    </section>
  );
}
