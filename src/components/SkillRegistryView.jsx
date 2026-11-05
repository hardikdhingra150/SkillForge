import { useCallback, useEffect, useId, useRef, useState } from "react";
import { getSkillRegistry } from "../api/skillforgeProcess.js";
import { restoreVersion, retireVersion } from "../api/review.js";
import { downloadBundle, getMcpConfig, importSkill } from "../api/skills.js";

function UseInAgents() {
  const [config, setConfig] = useState(null);
  const [copied, setCopied] = useState("");
  async function load(event) {
    if (event.target.open && !config) {
      try { setConfig(await getMcpConfig()); } catch { setConfig({ clients: [], notes: "Start the API to see the commands." }); }
    }
  }
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); setCopied(text); setTimeout(() => setCopied(""), 1500); } catch { setCopied(""); }
  }
  return (
    <details className="sf-registry__agents" onToggle={load}>
      <summary>Use these skills in Claude Code, Codex or Cursor (MCP)</summary>
      <p>Every validated skill below becomes a tool your coding agents can call. It runs in the same sandbox and passes the same checks.</p>
      {config?.clients?.map((client) => (
        <div key={client.name} className="sf-registry__agent">
          <span>{client.name}</span>
          <pre>{client.command}</pre>
          <button onClick={() => copy(client.command)}>{copied === client.command ? "Copied" : "Copy"}</button>
        </div>
      ))}
      {config?.notes && <p className="sf-registry__count">{config.notes}</p>}
    </details>
  );
}
import "./skill-registry.css";

function mergeVersions(previous, incoming) {
  const values = new Map(previous.map((item) => [JSON.stringify([item.skill_id, item.version]), item]));
  for (const item of incoming) values.set(JSON.stringify([item.skill_id, item.version]), item);
  return [...values.values()];
}

// Every loaded version of one skill, oldest first: v1.0.0 → v1.1.0 (repaired) → …
function lineage(items, skill) {
  return items
    .filter((item) => item.skill_id === skill.skill_id)
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
}

function Lineage({ family, current }) {
  if (family.length < 2) return null;
  return (
    <ol className="sf-registry__lineage" aria-label="Version lineage">
      {family.map((item) => (
        <li key={item.version} data-current={item.version === current.version || undefined}
          data-status={item.status}>
          v{item.version}
          {item.origin !== "builtin" && <small> ({item.origin}{item.parent_version ? ` from v${item.parent_version}` : ""})</small>}
        </li>
      ))}
    </ol>
  );
}

// Ask why before retiring or restoring a version; the answer goes into the audit trail.
function ReasonForm({ action, onConfirm, onCancel }) {
  const id = useId();
  const [reason, setReason] = useState("");
  return (
    <form className="sf-registry__reason" onSubmit={(event) => { event.preventDefault(); onConfirm(reason.trim()); }}>
      <label htmlFor={id}>{action === "retire" ? "Why retire this version?" : "Why restore this version?"}</label>
      <input id={id} value={reason} maxLength={500} autoFocus onChange={(event) => setReason(event.target.value)}
        placeholder="Optional. Recorded in the audit trail." />
      <div>
        <button type="submit">{action === "retire" ? "Retire (roll back)" : "Restore"}</button>
        <button type="button" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

export default function SkillRegistryView({ onOpenWorkbench }) {
  const uid = useId();
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("");
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const activeRequest = useRef(null);
  // { key, action } while asking why a version is retired or restored.
  const [confirming, setConfirming] = useState(null);

  const applyPage = useCallback((page, append) => {
    setItems((previous) => append ? mergeVersions(previous, page.items) : page.items);
    setHasMore(page.has_more);
    setCursor(page.has_more ? {
      afterSkillId: page.next_after_skill_id,
      afterVersion: page.next_after_version,
    } : null);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    activeRequest.current = controller;
    setItems([]);
    setCursor(null);
    setHasMore(false);
    setError("");
    setLoading(true);
    getSkillRegistry({ status, query }, controller.signal).then((page) => {
      if (!controller.signal.aborted) applyPage(page, false);
    }).catch((failure) => {
      if (!controller.signal.aborted) setError(failure.message);
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => activeRequest.current?.abort();
  }, [status, query, refresh, applyPage]);

  const importRef = useRef(null);
  const [importNote, setImportNote] = useState("");

  async function importFile(file) {
    if (!file) return;
    setError("");
    setImportNote("");
    try {
      const bundle = JSON.parse(await file.text());
      const row = await importSkill(bundle);
      setImportNote(`Imported ${row.skill_id} v${row.version}: re-proven with ${row.validation?.test_count ?? 0} fixtures in the sandbox.`);
      setRefresh((n) => n + 1);
    } catch (failure) {
      setError(failure instanceof SyntaxError ? "That file is not a SkillForge bundle (invalid JSON)." : failure.message);
    } finally {
      if (importRef.current) importRef.current.value = "";
    }
  }

  async function changeStatus(skill, action, reason) {
    setError("");
    setConfirming(null);
    try {
      const updated = action === "retire"
        ? await retireVersion(skill.skill_id, skill.version, reason)
        : await restoreVersion(skill.skill_id, skill.version, reason);
      setItems((previous) => previous.map((item) => (
        item.skill_id === skill.skill_id && item.version === skill.version ? { ...item, status: updated.status } : item
      )));
    } catch (failure) {
      setError(failure.message);
    }
  }

  async function loadMore() {
    if (loading || !cursor) return;
    const controller = new AbortController();
    activeRequest.current = controller;
    setLoading(true);
    setError("");
    try {
      const page = await getSkillRegistry({ status, query, ...cursor }, controller.signal);
      if (!controller.signal.aborted) applyPage(page, true);
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure.message);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  return (
    <section className="sf-registry" aria-labelledby={`${uid}-title`}>
      <header className="sf-registry__header">
        <div>
          <p className="sf-registry__eyebrow">Registered capabilities</p>
          <h1 id={`${uid}-title`}>Your skill library.</h1>
          <p>Explore the versions, validation evidence, and source identity stored in your registry.</p>
        </div>
        <div className="sf-registry__actions">
          <button onClick={() => setRefresh((value) => value + 1)} disabled={loading}>Refresh registry</button>
          <button onClick={() => importRef.current?.click()}>Import bundle</button>
          <input ref={importRef} type="file" accept=".json,application/json" hidden onChange={(e) => importFile(e.target.files?.[0])} />
          <button onClick={onOpenWorkbench}>Open workbench</button>
        </div>
      </header>
      {importNote && <p className="sf-registry__count" role="status">{importNote}</p>}
      <UseInAgents />

      <form className="sf-registry__filters" onSubmit={(event) => {
        event.preventDefault();
        setQuery(draft.trim());
      }}>
        <label htmlFor={`${uid}-search`}>Search skills
          <input id={`${uid}-search`} value={draft} maxLength={100}
            onChange={(event) => setDraft(event.target.value)} placeholder="Search by ID, capability, or version" />
        </label>
        <button type="submit">Search</button>
        <label htmlFor={`${uid}-status`}>Status
          <select id={`${uid}-status`} value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">All statuses</option>
            <option value="validated">Validated</option>
            <option value="draft">Draft</option>
            <option value="retired">Retired</option>
          </select>
        </label>
      </form>

      <p className="sf-registry__count" role="status">
        {loading ? "Loading registry…" : `${items.length} version${items.length === 1 ? "" : "s"} loaded`}
        {!loading && hasMore ? " · More versions available" : ""}
      </p>
      {error && <div className="sf-registry__error" role="alert">
        <p>{error}</p><button onClick={() => setRefresh((value) => value + 1)}>Retry</button>
      </div>}
      {!loading && !error && items.length === 0 && (
        <div className="sf-registry__empty">
          <h2>{query || status ? "No matching versions." : "No registered versions yet."}</h2>
          <p>{query || status ? "Try another search or status filter." : "Registered skills will appear here with their recorded validation evidence."}</p>
        </div>
      )}

      <div className="sf-registry__grid">
        {items.map((skill) => {
          const checks = Array.isArray(skill.validation?.tests) ? skill.validation.tests : [];
          return <article className="sf-registry__card" key={JSON.stringify([skill.skill_id, skill.version])}>
            <div className="sf-registry__card-top">
              <span className="sf-registry__badge" data-status={skill.status}>{skill.status}</span>
              <span className="sf-registry__version">v{skill.version}</span>
            </div>
            <h2>{skill.skill_id.replaceAll("_", " ")}</h2>
            <code>{skill.skill_id}</code>
            <Lineage family={lineage(items, skill)} current={skill} />
            <dl>
              <div><dt>Capability</dt><dd>{skill.capability}</dd></div>
              <div><dt>Origin</dt><dd>{skill.parent_version ? `${skill.origin} from v${skill.parent_version}` : skill.origin || "builtin"}</dd></div>
              <div><dt>Registered</dt><dd>{new Date(skill.created_at).toLocaleString()}</dd></div>
              <div><dt>Recorded checks</dt><dd>{checks.length}</dd></div>
              <div><dt>Validation result</dt><dd>{skill.validation?.passed === true ? "Passed" : skill.validation?.passed === false ? "Failed" : "No result recorded"}</dd></div>
            </dl>
            {skill.change?.diff && <details className="sf-registry__change" open>
              <summary>What changed · {skill.change.strategy?.replaceAll("_", " ")}</summary>
              <p>{skill.change.summary}</p>
              {skill.change.failure && <p className="sf-registry__failure">Fixed failure: <code>{skill.change.failure.code}</code> {skill.change.failure.message}</p>}
              <pre className="sf-registry__diff">{skill.change.diff.split("\n").map((line, index) => (
                <span key={index} data-kind={line.startsWith("+") && !line.startsWith("+++") ? "add" : line.startsWith("-") && !line.startsWith("---") ? "del" : undefined}>{line}{"\n"}</span>
              ))}</pre>
            </details>}
            <div className="sf-registry__actions sf-registry__version-actions">
              {skill.status === "validated" && <button onClick={() => setConfirming({ key: `${skill.skill_id}@${skill.version}`, action: "retire" })} title="Stop using this version; the previous validated version is used again">Retire (roll back)</button>}
              {skill.status === "retired" && skill.source_code && <button onClick={() => setConfirming({ key: `${skill.skill_id}@${skill.version}`, action: "restore" })}>Restore</button>}
              {skill.source_code && <button className="sf-registry__export" onClick={() => downloadBundle(skill.skill_id, skill.version).catch((failure) => setError(failure.message))}>Export bundle</button>}
            </div>
            {confirming?.key === `${skill.skill_id}@${skill.version}` && (
              <ReasonForm
                action={confirming.action}
                onCancel={() => setConfirming(null)}
                onConfirm={(reason) => changeStatus(skill, confirming.action, reason)}
              />
            )}
            <details>
              <summary>Validation evidence and implementation hash</summary>
              {checks.length > 0 && <ul>{checks.map((check, index) => (
                <li key={`${check.name}:${index}`}>
                  {check.name}: {check.passed === true ? "Passed" : check.passed === false ? "Failed" : "No result"}
                </li>
              ))}</ul>}
              <p>Implementation SHA-256</p>
              <code className="sf-registry__hash">{skill.implementation_hash}</code>
            </details>
          </article>;
        })}
      </div>
      {hasMore && <button className="sf-registry__more" onClick={loadMore} disabled={loading}>
        {loading ? "Loading…" : "Load more versions"}
      </button>}
    </section>
  );
}
