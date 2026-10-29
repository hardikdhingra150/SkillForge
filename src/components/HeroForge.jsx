import React, { useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowRight, ArrowUpRight, CheckCheck, Code2, FileText, FlaskConical, GitBranch, Layers3, Play, RotateCcw, Search, ShieldCheck, Sparkles, Terminal, TriangleAlert, Zap } from 'lucide-react';
import { PixelSprite } from './PixelArt';
import KineticType from './KineticType';

const STAGES = [
  { name: 'Discover', icon: Search },
  { name: 'Create', icon: Code2 },
  { name: 'Execute', icon: Zap },
  { name: 'Evaluate', icon: FlaskConical },
  { name: 'Repair', icon: GitBranch },
  { name: 'Version', icon: Layers3 },
  { name: 'Reuse', icon: RotateCcw },
];

// One illustrative run of the learning loop, replayed by the hero console.
const RUN = [
  { stage: 0, tag: 'TASK', text: '“Show revenue by product from quarterly_sales.csv”', tone: 'task', ms: 1500 },
  { stage: 0, tag: 'FIND', text: 'registry.find("sales csv")  →  no matching skill', ms: 1100 },
  { stage: 1, tag: 'MAKE', text: 'sales_analysis v1.0  ·  contract + approved tools', ms: 1200 },
  { stage: 2, tag: 'RUN', text: 'read_csv(quarterly_sales.csv)  ·  24 rows', ms: 1100 },
  { stage: 3, tag: 'FAIL', text: 'KeyError: "revenue"  ·  column is called "Sales"', tone: 'error', ms: 1700 },
  { stage: 4, tag: 'PATCH', text: 'column_map["revenue"] = "Sales"', tone: 'repair', ms: 1200 },
  { stage: 4, tag: 'TEST', text: '3 / 3 checks passed  ·  aliases, totals, nulls', tone: 'ok', ms: 1200 },
  { stage: 5, tag: 'SAVE', text: 'sales_analysis v1.1  →  registry', tone: 'ok', ms: 1200 },
  { stage: 6, tag: 'REUSE', text: 'next run: 0 repairs  ·  revenue $18,420', tone: 'ok', ms: 3600 },
];


export function CountUp({ value, pad = 0, suffix = '', display, run }) {
  const [shown, setShown] = useState(run ? 0 : value);
  useEffect(() => {
    if (value == null) return undefined;
    if (!run) { setShown(value); return undefined; }
    let frame = 0;
    const start = performance.now();
    const tick = now => {
      const t = Math.min(1, (now - start) / 1400);
      setShown(Math.round(value * (1 - Math.pow(1 - t, 3))));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, run]);
  if (value == null) return <>{display}</>;
  return <>{String(shown).padStart(pad, '0')}{suffix}</>;
}

/** The hero's centrepiece: a console that replays one run of the learning loop. */
function ForgeConsole({ motion }) {
  const ref = useRef();
  const [line, setLine] = useState(motion ? 0 : RUN.length - 1);
  const [visible, setVisible] = useState(true);
  const [cycle, setCycle] = useState(0);

  useEffect(() => {
    const node = ref.current;
    if (!node || !('IntersectionObserver' in window)) return undefined;
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting), { threshold: 0.15 });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!motion) { setLine(RUN.length - 1); return undefined; }
    if (!visible) return undefined;
    const timer = setTimeout(() => {
      if (line < RUN.length - 1) setLine(line + 1);
      else { setCycle(c => c + 1); setLine(0); }
    }, RUN[line].ms);
    return () => clearTimeout(timer);
  }, [line, motion, visible]);

  const stage = RUN[line].stage;
  const failed = line === 4;
  const repaired = line >= 5;
  const saved = line >= 7;
  const testsPassed = line >= 6 ? 3 : line === 4 ? 0 : null;

  return <div className={`hx-stage ${failed ? 'is-failing' : ''} ${saved ? 'is-saved' : ''}`} ref={ref} aria-label="Illustrative replay of a SkillForge learning loop">
    <div className="hx-window-bar">
      <span className="hx-window-dots" aria-hidden="true"><i /><i /><i /></span>
      <span className="hx-window-title"><Terminal size={13} />forge://workspace-001/run</span>
      <span className="hx-live"><i />{motion ? 'LIVE REPLAY' : 'REPLAY PAUSED'}</span>
    </div>

    <div className="hx-pipeline" aria-hidden="true">
      {STAGES.map((s, i) => <span key={s.name} className={`${i < stage ? 'done' : ''} ${i === stage ? 'current' : ''} ${i === 3 && failed ? 'fail' : ''}`}>
        <s.icon size={13} /><b>{s.name}</b>
      </span>)}
      <i className="hx-pipeline-fill" style={{ '--p': stage / (STAGES.length - 1) }} />
    </div>

    <div className="hx-stage-body">
      <ol className="hx-log" key={cycle}>
        {RUN.slice(0, line + 1).map((entry, i) => <li key={i} className={`${entry.tone || ''} ${i === line ? 'typing' : ''}`} style={{ '--chars': entry.text.length }}>
          <span className="hx-log-time">00:{String(Math.round(RUN.slice(0, i).reduce((t, e) => t + e.ms, 0) / 1000)).padStart(2, '0')}</span>
          <span className="hx-log-tag">{entry.tag}</span>
          <span className="hx-log-text">{entry.text}</span>
        </li>)}
        <li className="hx-log-cursor" aria-hidden="true"><span>›</span><b /></li>
      </ol>

      <aside className="hx-skill">
        <div className="hx-skill-top"><span>SKILL CARD</span><span className={`hx-skill-badge ${saved ? 'ok' : failed ? 'fail' : ''}`}>{saved ? 'VALIDATED' : failed ? 'NEEDS REPAIR' : line >= 2 ? 'CANDIDATE' : 'SEARCHING'}</span></div>
        <div className="hx-skill-name">
          <PixelSprite kind={failed || line === 5 ? 'patch' : saved ? 'byte' : 'scout'} />
          <div><strong>{line >= 2 ? 'sales_analysis' : '—'}</strong><small>{line >= 2 ? <>v<span key={repaired ? 'b' : 'a'} className="hx-version">{saved ? '1.1' : '1.0'}</span></> : 'no match yet'}</small></div>
        </div>
        <div className="hx-diff" aria-hidden="true">
          <span className={`removed ${repaired ? 'struck' : ''}`}><b>−</b>column = "revenue"</span>
          <span className={`added ${repaired ? 'shown' : ''}`}><b>+</b>column = "Sales"</span>
        </div>
        <div className="hx-tests">
          <span>TESTS</span>
          <div>{[0, 1, 2].map(i => <i key={i} className={testsPassed == null ? '' : i < testsPassed ? 'pass' : 'fail'} />)}</div>
          <b>{testsPassed == null ? '— / 3' : `${testsPassed} / 3`}</b>
        </div>
        <div className="hx-result"><span>RESULT</span><strong>{line >= 8 ? '$18,420' : failed ? 'error' : '…'}</strong></div>
      </aside>
    </div>

    <div className="hx-stage-foot"><span>ILLUSTRATIVE DEMO · SAMPLE DATA</span><span>{failed ? <><TriangleAlert size={12} />A failure is useful information.</> : saved ? <><CheckCheck size={12} />Fixed. Tested. Remembered.</> : <><Sparkles size={12} />Learning in progress…</>}</span></div>
  </div>;
}

export default function HeroForge({ motion, onEnter, onDemo, onLearn, onToast }) {
  return <section className="forge-hero hx" id="top">
    <div className="hx-backdrop" aria-hidden="true"><i className="hx-grid" /><i className="hx-glow" /></div>
    <div className="forge-hero-overline"><span><i />SELF-EVOLVING SKILL INFRASTRUCTURE</span><span>BUILT TO LEARN. MADE TO LAST.</span></div>

    <div className="hx-copy">
      <button className="hx-pill" onClick={onLearn}><span className="hx-pill-tag">NEW</span>Skills that repair themselves, then remember the fix<ArrowRight size={14} /></button>
      <h1 className="hx-title" aria-label="Every failure becomes a skill.">
        <span className="hx-title-line" aria-hidden="true">Every failure</span>
        <span className="hx-title-line hx-title-second" aria-hidden="true">
          <span className="hx-title-soft">becomes a</span>
          <span className="hx-title-pixel"><KineticType text="SKILL." /></span>
          <span className="hx-title-pet"><PixelSprite kind="scout" interactive title="Say hello to Scout" onPoke={() => onToast('Scout is looking for your next great idea.')} /></span>
        </span>
      </h1>
      <p className="hx-sub">SkillForge gives your agents a way to <strong>build what’s missing, repair what breaks, and keep what works</strong>: tested, versioned skills they reuse on every run after.</p>
      <div className="hx-actions">
        <button className="forge-cta" onClick={onEnter}>Open your workspace <ArrowUpRight size={18} /></button>
        <button className="hx-try" onClick={onDemo}><Play size={14} /><span>Try it:</span><code>“Show revenue by product”</code><ArrowRight size={14} /></button>
      </div>
      <div className="hx-proof"><span><ShieldCheck size={14} />Test before trust</span><span><Layers3 size={14} />Every version remembered</span><span><FileText size={14} />Full repair history</span></div>
    </div>

    <div className="hx-stage-wrap"><ForgeConsole motion={motion} /></div>

    <button className="hx-scroll-cue" onClick={onLearn} aria-label="See how it learns"><span>SCROLL TO SEE HOW IT LEARNS</span><ArrowDown size={14} /></button>
  </section>;
}

