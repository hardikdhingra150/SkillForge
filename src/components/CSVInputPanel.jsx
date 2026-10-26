import { useEffect, useRef, useState } from "react";
import { confirmCSVMapping, getCSVInput, uploadCSVInput } from "../api/skillforgeProcess.js";

const cellStyle = { border: "1px solid #667085", padding: "6px 10px", textAlign: "left" };

export default function CSVInputPanel({ execution, events, onUpdated }) {
  const [input, setInput] = useState(null);
  const [file, setFile] = useState(null);
  const [product, setProduct] = useState("");
  const [revenue, setRevenue] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const actionController = useRef(null);

  useEffect(() => () => actionController.current?.abort(), []);

  useEffect(() => {
    const controller = new AbortController();
    getCSVInput(execution.execution_id, controller.signal).then((value) => {
      if (controller.signal.aborted) return;
      setInput(value);
      setProduct(value.column_mapping?.product || "");
      setRevenue(value.column_mapping?.revenue || "");
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
      setProduct(value.column_mapping?.product || "");
      setRevenue(value.column_mapping?.revenue || "");
      onUpdated();
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure.message);
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  if (!canUpload && !input && !error) return null;

  return (
    <section style={{ borderTop: "1px solid #667085", marginTop: 20, paddingTop: 20 }}>
      <h3>Sales CSV and columns</h3>
      {error && <p role="alert" className="sf-process__error">{error}</p>}
      {canUpload && !input?.confirmed && (
        <form onSubmit={(event) => {
          event.preventDefault();
          if (!file) return;
          perform((signal) => uploadCSVInput(execution.execution_id, file, signal));
        }}>
          <label>Sales CSV
            <input type="file" accept=".csv,text/csv" required disabled={busy}
              onChange={(event) => setFile(event.target.files?.[0] || null)} />
          </label>
          <p className="sf-process__muted">UTF-8 CSV · up to 1 MiB · up to 10,000 data rows</p>
          <button type="submit" disabled={busy || !file}>
            {busy ? "Saving…" : input ? "Replace CSV" : "Upload CSV"}
          </button>
        </form>
      )}
      {input && (
        <>
          <p><strong>{input.filename}</strong> · {input.row_count} rows · {input.headers.length} columns</p>
          <div style={{ overflowX: "auto", margin: "12px 0" }}>
            <table style={{ borderCollapse: "collapse", width: "100%" }}>
              <caption>Preview of the first {input.preview.length} data rows</caption>
              <thead><tr>{input.headers.map((header) => <th key={header} style={cellStyle}>{header}</th>)}</tr></thead>
              <tbody>{input.preview.map((row, index) => (
                <tr key={index}>{row.map((value, column) => <td key={column} style={cellStyle}>{value}</td>)}</tr>
              ))}</tbody>
            </table>
          </div>
          {input.confirmed ? (
            <p className="sf-process__notice">
              Confirmed columns: product = {input.column_mapping.product}; revenue = {input.column_mapping.revenue}.
            </p>
          ) : canUpload && (
            <form onSubmit={(event) => {
              event.preventDefault();
              perform((signal) => confirmCSVMapping(execution.execution_id, {
                file_sha256: input.sha256, file_version: input.version,
                product_column: product, revenue_column: revenue,
              }, signal));
            }}>
              <label>Product column
                <select required value={product} disabled={busy} onChange={(event) => setProduct(event.target.value)}>
                  <option value="">Choose a column</option>
                  {input.headers.map((header) => <option key={header} value={header}>{header}</option>)}
                </select>
              </label>
              <label>Revenue column
                <select required value={revenue} disabled={busy} onChange={(event) => setRevenue(event.target.value)}>
                  <option value="">Choose a column</option>
                  {input.headers.map((header) => <option key={header} value={header}>{header}</option>)}
                </select>
              </label>
              <button type="submit" disabled={busy || !product || !revenue || product === revenue}>
                {busy ? "Confirming…" : "Confirm columns for revenue by product"}
              </button>
            </form>
          )}
        </>
      )}
    </section>
  );
}
