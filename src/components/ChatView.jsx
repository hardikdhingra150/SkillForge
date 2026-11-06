import { useCallback, useEffect, useId, useRef, useState } from "react";
import { ArrowUpRight, Bot, Check, CircleCheck, Copy, FileSpreadsheet, LoaderCircle, MessagesSquare, Paperclip, Plus, RefreshCw, Send, Trash2, Wrench, X } from "lucide-react";
import {
  createConversation,
  deleteConversation,
  getConversation,
  getProviders,
  listConversations,
  sendMessage,
  streamConversation,
  uploadAttachment,
} from "../api/chat.js";
import "./chat.css";

const POLL_MS = 1500;

const SUGGESTIONS = [
  "Extract the email addresses from: write to hi@acme.io or team@forge.dev",
  "Convert 100 degrees Celsius to Fahrenheit",
  "Add up these numbers: 1, 2.5, 3",
  "In one sentence, what is a skill registry?",
  "Extract the emails from: ana@acme.io, bo@forge.dev, cy@acme.io — then count them by domain",
];

const STEP_ICON = {
  skill_created: CircleCheck, skill_promoted: Wrench, skill_ran: CircleCheck, verified: CircleCheck,
  failed: Wrench, skill_failed: Wrench, verify_failed: Wrench, smith_rejected: Wrench,
};

const EVENT_LABEL = { created: "New skill", reused: "Reused", repaired: "Repaired", pipeline: "Multi-step" };

const PROVIDER_LABEL = { auto: "Auto", claude: "Claude", codex: "Codex", ollama: "Local" };

/** "Auto" lets the scoreboard pick the model per task; it is available whenever any model is. */
function withAuto(list) {
  const any = list.some((p) => p.available);
  return [{ id: "auto", label: "Auto (scoreboard routing)", kind: "auto", available: any, models: [], default_model: null,
            detail: any ? "Routes each task to the cheapest model with a good record." : "Connect at least one model.", setup: [] },
          ...list];
}

/** Tiny, safe inline formatting: **bold** and `code`. Everything else is plain text. */
function Inline({ text }) {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={index}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={index}>{part.slice(1, -1)}</code>;
    return <span key={index}>{part}</span>;
  });
}

function Value({ value }) {
  if (Array.isArray(value)) {
    return value.length ? <ul>{value.map((item, i) => <li key={i}><Value value={item} /></li>)}</ul> : <em>empty</em>;
  }
  if (value && typeof value === "object") return <code>{JSON.stringify(value)}</code>;
  return <span>{String(value)}</span>;
}

function FileChip({ file, onRemove }) {
  return (
    <span className="sf-chat__file">
      <FileSpreadsheet size={13} /><b>{file.filename}</b>
      <small>{file.row_count} rows · {file.headers.join(", ")}</small>
      {onRemove && <button type="button" onClick={onRemove} aria-label={`Remove ${file.filename}`}><X size={12} /></button>}
    </span>
  );
}

function SkillCard({ skill, onOpenLibrary }) {
  return (
    <div className="sf-chat__skill" data-event={skill.event}>
      {skill.steps?.length > 1 && (
        <ol className="sf-chat__pipeline">
          {skill.steps.map((step, i) => (
            <li key={i}><span className="sf-chat__badge" data-event={step.event}>{EVENT_LABEL[step.event] || step.event}</span>
              <code>{step.skill_id} v{step.version}</code></li>
          ))}
        </ol>
      )}
      <div className="sf-chat__skill-top">
        <span className="sf-chat__badge">{EVENT_LABEL[skill.event] || skill.event}</span>
        <code>{skill.skill_id} v{skill.version}</code>
        {skill.parent_version && <span className="sf-chat__muted">from v{skill.parent_version}</span>}
        <button className="sf-chat__link" onClick={onOpenLibrary}>Skill library <ArrowUpRight size={12} /></button>
      </div>
      <dl>
        {Object.entries(skill.output || {}).map(([key, value]) => (
          <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd><Value value={value} /></dd></div>
        ))}
      </dl>
    </div>
  );
}

function Steps({ steps, pending }) {
  if (!steps.length && !pending) return null;
  return (
    <details className="sf-chat__steps" open={pending}>
      <summary>{pending ? "Working…" : `${steps.length} steps`}</summary>
      <ol>
        {steps.map((step, index) => {
          const Icon = STEP_ICON[step.kind];
          return <li key={index} data-kind={step.kind}>{Icon ? <Icon size={13} /> : <i />}<span>{step.text}</span></li>;
        })}
        {pending && <li data-kind="live"><LoaderCircle size={13} className="sf-chat__spin" /><span>Thinking…</span></li>}
      </ol>
    </details>
  );
}

function CopyCommand({ command }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }
  return (
    <div className="sf-chat__command">
      <code>{command}</code>
      <button type="button" onClick={copy} aria-label={`Copy ${command}`}>{copied ? <Check size={13} /> : <Copy size={13} />}</button>
    </div>
  );
}

function SetupCard({ provider, onRecheck }) {
  return (
    <div className="sf-chat__setup" role="status">
      <p><strong>{provider.label} is not connected.</strong> {provider.detail}</p>
      <p className="sf-chat__muted">Run these in a terminal, then press Re-check:</p>
      <ol>
        {provider.setup.map((step) => (
          <li key={step.command}><span>{step.label}</span><CopyCommand command={step.command} /></li>
        ))}
      </ol>
      <button type="button" className="sf-chat__recheck" onClick={onRecheck}><RefreshCw size={13} /> Re-check</button>
    </div>
  );
}

function Message({ message, onOpenLibrary }) {
  if (message.role === "user") {
    return (
      <div className="sf-chat__message" data-role="user">
        <p>{message.content}</p>
        {message.attachments?.length > 0 && <div className="sf-chat__files">{message.attachments.map((f) => <FileChip key={f.id} file={f} />)}</div>}
      </div>
    );
  }
  const pending = message.status === "pending";
  return (
    <div className="sf-chat__message" data-role="assistant" data-status={message.status}>
      <div className="sf-chat__who"><Bot size={14} /> {message.provider}{message.model ? ` · ${message.model}` : ""}</div>
      <Steps steps={message.steps || []} pending={pending} />
      {!pending && message.content && <p className="sf-chat__content">{message.content.split("\n").map((line, i) => (
        <span key={i}><Inline text={line} />{"\n"}</span>
      ))}</p>}
      {message.skill?.event === "clarify" && <span className="sf-chat__badge sf-chat__ask">Question for you · reply below</span>}
      {message.skill && message.skill.event !== "clarify" && <SkillCard skill={message.skill} onOpenLibrary={onOpenLibrary} />}
    </div>
  );
}

export default function ChatView({ onOpenLibrary, initialDraft = "", onDraftUsed }) {
  const uid = useId();
  const [providers, setProviders] = useState([]);
  const [providerId, setProviderId] = useState("");
  const [model, setModel] = useState("");
  const [conversations, setConversations] = useState([]);
  const [active, setActive] = useState(null);
  const [draft, setDraft] = useState(initialDraft);
  const [error, setError] = useState("");
  // A request handed over from the Workbench starts in the message box once; forget it after that.
  useEffect(() => {
    if (initialDraft) onDraftUsed?.();
  }, [initialDraft, onDraftUsed]);
  const [sending, setSending] = useState(false);
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef(null);
  const threadRef = useRef(null);

  const provider = providers.find((p) => p.id === providerId);
  const pending = active?.messages?.some((m) => m.status === "pending");

  const loadProviders = useCallback(async (refresh = false) => {
    try {
      const list = withAuto(await getProviders({ refresh }));
      setProviders(list);
      setProviderId((current) => current || (list[0].available ? "auto" : list[0]?.id) || "");
    } catch (failure) {
      setError(failure.message);
    }
  }, []);

  const loadConversations = useCallback(async () => {
    try {
      setConversations(await listConversations());
    } catch (failure) {
      setError(failure.message);
    }
  }, []);

  useEffect(() => {
    loadProviders();
    loadConversations();
  }, [loadProviders, loadConversations]);

  useEffect(() => {
    if (provider && !provider.models.includes(model)) setModel(provider.default_model || "");
  }, [provider, model]);

  // Stream the open conversation while a reply is in progress; poll only if the stream fails.
  const [streamFailed, setStreamFailed] = useState(false);
  const activeId = active?.id;
  useEffect(() => {
    if (!activeId || !pending || streamFailed || typeof EventSource === "undefined") return undefined;
    return streamConversation(activeId, {
      onUpdate: setActive,
      onDone: loadConversations,
      onError: () => setStreamFailed(true),
    });
  }, [activeId, pending, streamFailed, loadConversations]);

  useEffect(() => {
    if (!active?.id || !pending || !streamFailed) return undefined;
    const timer = setTimeout(async () => {
      try {
        const next = await getConversation(active.id);
        setActive(next);
        if (!next.messages.some((m) => m.status === "pending")) loadConversations();
      } catch (failure) {
        setError(failure.message);
      }
    }, POLL_MS);
    return () => clearTimeout(timer);
  }, [active, pending, streamFailed, loadConversations]);

  const messageCount = active?.messages?.length ?? 0;
  const lastStepCount = active?.messages?.at(-1)?.steps?.length ?? 0;
  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [messageCount, lastStepCount]);

  async function open(id) {
    setError("");
    try {
      setActive(await getConversation(id));
    } catch (failure) {
      setError(failure.message);
    }
  }

  async function ensureConversation() {
    if (active?.id) return active;
    const created = await createConversation(providerId, model);
    const fresh = { ...created, messages: [] };
    setActive(fresh);
    return fresh;
  }

  async function attach(list) {
    const picked = [...list].filter((f) => f.name.toLowerCase().endsWith(".csv"));
    if (!picked.length) { setError("Attach a .csv file."); return; }
    setUploading(true);
    setError("");
    try {
      const conversation = await ensureConversation();
      for (const file of picked.slice(0, 5)) {
        const uploaded = await uploadAttachment(conversation.id, file);
        setFiles((current) => [...current, uploaded]);
      }
      loadConversations();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function send(text) {
    const content = (text ?? draft).trim();
    if (!content || sending || pending || uploading) return;
    if (!provider?.available) {
      setError(provider ? `${provider.label}: ${provider.detail}` : "Choose a model first.");
      return;
    }
    setSending(true);
    setStreamFailed(false);
    setError("");
    try {
      const conversation = active?.id ? active : await createConversation(providerId, model);
      await sendMessage(conversation.id, content, providerId, model, files.map((f) => f.id));
      setDraft("");
      setFiles([]);
      setActive(await getConversation(conversation.id));
      loadConversations();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setSending(false);
    }
  }

  async function remove(id) {
    try {
      await deleteConversation(id);
      if (active?.id === id) setActive(null);
      loadConversations();
    } catch (failure) {
      setError(failure.message);
    }
  }

  return (
    <section className="sf-chat" aria-labelledby={`${uid}-title`}>
      <aside className="sf-chat__sidebar">
        <button className="sf-chat__new" onClick={() => { setActive(null); setDraft(""); setFiles([]); }}><Plus size={15} /> New chat</button>
        <p className="sf-chat__label">Recent</p>
        <ul>
          {conversations.map((c) => (
            <li key={c.id} data-active={active?.id === c.id || undefined}>
              <button className="sf-chat__conv" onClick={() => open(c.id)} title={c.title}>
                <MessagesSquare size={13} /><span>{c.title}</span>
              </button>
              <button className="sf-chat__delete" onClick={() => remove(c.id)} aria-label={`Delete ${c.title}`}><Trash2 size={13} /></button>
            </li>
          ))}
          {!conversations.length && <li className="sf-chat__muted">No chats yet.</li>}
        </ul>
      </aside>

      <div className="sf-chat__main">
        <header className="sf-chat__header">
          <div>
            <p className="sf-chat__label">Ask anything · skills are created, reused and repaired as you go</p>
            <h1 id={`${uid}-title`}>{active?.title || "Chat with your skills"}</h1>
          </div>
          <div className="sf-chat__providers" role="radiogroup" aria-label="Model provider">
            {providers.map((p) => (
              <button key={p.id} role="radio" aria-checked={providerId === p.id} data-available={p.available}
                      title={p.detail} onClick={() => setProviderId(p.id)}>
                <i />{PROVIDER_LABEL[p.id] || p.label}
              </button>
            ))}
            {provider?.models?.length > 1 && (
              <select aria-label="Model" value={model} onChange={(e) => setModel(e.target.value)}>
                {provider.models.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            )}
            <button className="sf-chat__icon" onClick={() => loadProviders(true)} aria-label="Refresh provider status"><RefreshCw size={14} /></button>
          </div>
        </header>
        {provider && !provider.available && provider.setup?.length > 0 && <SetupCard provider={provider} onRecheck={() => loadProviders(true)} />}
        {provider && !provider.available && !provider.setup?.length && <p className="sf-chat__notice">{provider.detail}</p>}
        {error && <p className="sf-chat__error" role="alert">{error}</p>}

        <div className="sf-chat__thread" ref={threadRef} aria-live="polite">
          {!active?.messages?.length && (
            <div className="sf-chat__empty">
              <Bot size={28} />
              <h2>What should your agents learn today?</h2>
              <p>Ask a question, or give a task. Repeatable tasks become tested skills you can reuse.</p>
              <div className="sf-chat__suggestions">
                {SUGGESTIONS.map((s) => <button key={s} onClick={() => send(s)} disabled={sending}>{s}</button>)}
              </div>
            </div>
          )}
          {active?.messages?.map((m) => <Message key={m.id} message={m} onOpenLibrary={onOpenLibrary} />)}
        </div>

        <form className={`sf-chat__composer ${dragging ? "is-dragging" : ""}`} onSubmit={(e) => { e.preventDefault(); send(); }}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)}
              onDrop={(e) => { e.preventDefault(); setDragging(false); attach(e.dataTransfer.files); }}>
          {files.length > 0 && (
            <div className="sf-chat__files sf-chat__files--pending">
              {files.map((f) => <FileChip key={f.id} file={f} onRemove={() => setFiles((c) => c.filter((x) => x.id !== f.id))} />)}
            </div>
          )}
          <input ref={fileRef} type="file" accept=".csv,text/csv" multiple hidden onChange={(e) => attach(e.target.files)} />
          <button type="button" className="sf-chat__attach" onClick={() => fileRef.current?.click()} disabled={uploading || pending}
                  aria-label="Attach a CSV file" title="Attach a CSV file">
            {uploading ? <LoaderCircle size={16} className="sf-chat__spin" /> : <Paperclip size={16} />}
          </button>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder={pending ? "Waiting for the reply…" : files.length ? "What should I do with this file?" : "Ask anything, describe a task, or drop a CSV…"}
            rows={2}
            maxLength={8000}
            aria-label="Message"
          />
          <button type="submit" disabled={!draft.trim() || sending || pending} aria-label="Send">
            {sending ? <LoaderCircle size={16} className="sf-chat__spin" /> : <Send size={16} />}
          </button>
        </form>
      </div>
    </section>
  );
}
