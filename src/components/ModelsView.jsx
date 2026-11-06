import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { getProviders, getScoreboard } from "../api/chat.js";
import "./models.css";

const percent = (value) => (value == null ? "—" : `${Math.round(value * 100)}%`);

function Meter({ value }) {
  return <span className="sf-models__meter" aria-hidden="true"><i style={{ width: `${Math.round((value ?? 0) * 100)}%` }} /></span>;
}

export default function ModelsView({ onOpenStudio }) {
  const [board, setBoard] = useState(null);
  const [providers, setProviders] = useState([]);
  const [error, setError] = useState("");

  const load = useCallback(async (refresh = false) => {
    setError("");
    try {
      const [next, list] = await Promise.all([getScoreboard(), getProviders({ refresh })]);
      setBoard(next);
      setProviders(list);
    } catch (failure) {
      setError(failure.message);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const status = Object.fromEntries(providers.map((p) => [p.id, p]));

  return (
    <section className="sf-models" aria-labelledby="sf-models-title">
      <header className="sf-models__header">
        <div>
          <p className="sf-models__label"><i />Model scoreboard · built from real proofs</p>
          <h1 id="sf-models-title">Which model earns trust?</h1>
          <p className="sf-models__lead">Every skill a model writes must pass the sandbox, its worked examples and an independent verifier.
            These numbers are what actually happened. <strong>Auto</strong> routing uses them to pick the cheapest model that has proven itself for each task.</p>
        </div>
        <button className="sf-models__refresh" onClick={() => load(true)}><RefreshCw size={14} /> Refresh</button>
      </header>
      {error && <p className="sf-models__error" role="alert">{error}</p>}

      <div className="sf-models__grid">
        {(board?.providers || []).map((p) => {
          const s = status[p.provider];
          return (
            <article key={p.provider} className="sf-models__card" data-available={s?.available}>
              <div className="sf-models__card-top">
                <h2>{s?.label || p.provider}</h2>
                <span className="sf-models__status"><i />
                  {s?.available ? (s.kind === "connector" ? "connected · your computer" : "connected") : "not connected"}</span>
              </div>
              {s?.kind === "connector" && !s.available && (
                <p className="sf-models__connect">
                  Runs on your own computer, with your login.{" "}
                  {onOpenStudio && <button type="button" className="sf-models__link" onClick={onOpenStudio}>Connect it in the Studio</button>}
                </p>
              )}
              <dl>
                <div><dt>Success rate</dt><dd>{percent(p.success_rate)}<Meter value={p.success_rate} /></dd></div>
                <div><dt>First-try proofs</dt><dd>{percent(p.first_try_rate)}<Meter value={p.first_try_rate} /></dd></div>
                <div><dt>Skills proven</dt><dd>{p.skills_proven}</dd></div>
                <div><dt>Avg attempts</dt><dd>{p.avg_attempts ?? "—"}</dd></div>
                <div><dt>Overruled by verifier</dt><dd>{p.overruled}</dd></div>
                <div><dt>Wrong examples fixed</dt><dd>{p.examples_corrected}</dd></div>
                <div><dt>Escalated away</dt><dd>{p.escalated_away}</dd></div>
                <div><dt>Reuses of its skills</dt><dd>{p.reuses}</dd></div>
                <div><dt>As verifier: agrees</dt><dd>{percent(p.verifier_agree_rate)} <small>({p.verifier_checks})</small></dd></div>
              </dl>
            </article>
          );
        })}
      </div>

      <h2 className="sf-models__subhead">Routing by capability</h2>
      {!board?.capabilities?.length && <p className="sf-models__empty">No proofs recorded yet. Ask something repeatable in Chat with <strong>Auto</strong> selected.</p>}
      {board?.capabilities?.length > 0 && (
        <table className="sf-models__table">
          <thead><tr><th>Capability</th><th>Results per model</th><th>Auto routes to</th></tr></thead>
          <tbody>
            {board.capabilities.map((c) => (
              <tr key={c.capability}>
                <td><code>{c.capability}</code></td>
                <td>{Object.entries(c.providers).map(([provider, e]) => (
                  <span key={provider} className="sf-models__chip">{status[provider]?.label?.split(" (")[0] || provider}: {e.proven}✓ {e.exhausted ? `${e.exhausted}✗` : ""} {e.reused ? `· ${e.reused} reuse` : ""}</span>
                ))}</td>
                <td>{c.routed_to ? <strong>{status[c.routed_to]?.label?.split(" (")[0] || c.routed_to}</strong> : <em>cheapest first, then escalate</em>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
