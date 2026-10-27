import { useCallback, useEffect, useId, useRef, useState } from "react";
import { getSkillRegistry } from "../api/skillforgeProcess.js";
import "./skill-registry.css";

function mergeVersions(previous, incoming) {
  const values = new Map(previous.map((item) => [JSON.stringify([item.skill_id, item.version]), item]));
  for (const item of incoming) values.set(JSON.stringify([item.skill_id, item.version]), item);
  return [...values.values()];
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
          <button onClick={onOpenWorkbench}>Open workbench</button>
        </div>
      </header>

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
            <dl>
              <div><dt>Capability</dt><dd>{skill.capability}</dd></div>
              <div><dt>Registered</dt><dd>{new Date(skill.created_at).toLocaleString()}</dd></div>
              <div><dt>Recorded checks</dt><dd>{checks.length}</dd></div>
              <div><dt>Validation result</dt><dd>{skill.validation?.passed === true ? "Passed" : skill.validation?.passed === false ? "Failed" : "No result recorded"}</dd></div>
            </dl>
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
