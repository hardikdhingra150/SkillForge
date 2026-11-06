import React, { useEffect, useState } from 'react';
import { ArrowDown, ArrowRight, ArrowUpRight, CheckCheck, Clapperboard, FileText, Layers3, Play, ShieldCheck, Sparkles, Star, Terminal } from 'lucide-react';
import { PixelSprite } from './PixelArt';
import KineticType from './KineticType';
import { SavedSkills, SetupSteps, StatusPill } from './WorkspaceParts.jsx';

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

function count(value) {
  return value == null ? '—' : String(value).padStart(2, '0');
}

/** The hero's centrepiece: your real workspace, straight from the API (or how to start it). */
function WorkspacePulse({ workspace, onEnter }) {
  const online = workspace.status === 'online';
  const metrics = workspace.metrics;
  const numbers = [
    ['Saved skills', count(metrics?.skills)],
    ['Runs', count(metrics?.runs)],
    ['Success rate', metrics?.success_rate == null ? '—' : `${metrics.success_rate}%`],
    ['Repairs', count(metrics?.repairs)],
  ];

  return <div className="hx-stage hx-pulse" aria-label="Your SkillForge workspace">
    <div className="hx-window-bar">
      <span className="hx-window-dots" aria-hidden="true"><i /><i /><i /></span>
      <span className="hx-window-title"><Terminal size={13} />your workspace</span>
      <StatusPill status={workspace.status} />
    </div>

    {online ? <div className="hx-pulse-body">
      <dl className="hx-pulse-numbers">
        {numbers.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
      </dl>

      <div className="hx-pulse-lists">
        <section>
          <h2>Saved skills</h2>
          <SavedSkills skills={workspace.skills} limit={3} />
        </section>
      </div>
    </div> : <div className="hx-pulse-body">
      {workspace.status === 'checking'
        ? <p className="ws-empty">Looking for your SkillForge API…</p>
        : <SetupSteps status={workspace.status} onRetry={workspace.refresh} onOpenSettings={onEnter} />}
    </div>}

    <div className="hx-stage-foot">
      <span>{online ? 'LIVE FROM YOUR API' : 'RUNS ON YOUR MACHINE'}</span>
      <span>{online
        ? (metrics?.runs ? <><CheckCheck size={12} />All numbers are live.</> : <><Sparkles size={12} />Empty for now.</>)
        : <><ShieldCheck size={12} />Your data stays with you.</>}</span>
    </div>
  </div>;
}

// The project's source code. Starring it helps others find SkillForge.
const REPO_URL = 'https://github.com/hardikdhingra150/SkillForge';

export default function HeroForge({ workspace, onEnter, onSampleRun, onLearn, onToast, onTour }) {
  return <section className="forge-hero hx" id="top">
    <div className="hx-backdrop" aria-hidden="true"><i className="hx-grid" /><i className="hx-glow" /></div>
    <div className="forge-hero-overline"><span><i />SELF-EVOLVING SKILL INFRASTRUCTURE</span><span>BUILT TO LEARN. MADE TO LAST.</span></div>

    <div className="hx-copy">
      <button className="hx-pill" onClick={onLearn}><span className="hx-pill-tag">NEW</span>Skills that repair themselves, then remember the fix<ArrowRight size={14} /></button>
      <h1 className="hx-title" aria-label="Every failure becomes a skill.">
        <span className="hx-title-line" aria-hidden="true">Every failure</span>
        <span className="hx-title-line hx-title-second">
          <span className="hx-title-soft" aria-hidden="true">becomes a</span>
          <span className="hx-title-pixel" aria-hidden="true"><KineticType text="SKILL." /></span>
          <span className="hx-title-pet"><PixelSprite kind="scout" interactive title="Say hello to Scout" onPoke={() => onToast('Scout is looking for your next great idea.')} /></span>
        </span>
      </h1>
      <p className="hx-sub">SkillForge gives your agents a way to <strong>build what’s missing, repair what breaks, and keep what works</strong>: tested, versioned skills they reuse on every run after.</p>
      <div className="hx-actions">
        <button className="forge-cta" onClick={onEnter}>Open your workspace <ArrowUpRight size={18} /></button>
        <button className="hx-try" onClick={onSampleRun}><Play size={14} /><span>Try it with a sample file</span><ArrowRight size={14} /></button>
        {onTour && <button className="hx-try" onClick={onTour}><Clapperboard size={14} /><span>Watch the 2-minute tour</span></button>}
      </div>
      <div className="hx-proof"><span><ShieldCheck size={14} />Test before trust</span><span><Layers3 size={14} />Every version remembered</span><span><FileText size={14} />Full repair history</span></div>
      <a className="hx-star" href={REPO_URL} target="_blank" rel="noopener noreferrer">
        <Star size={14} />Like SkillForge? Star it on GitHub<ArrowUpRight size={13} />
      </a>
    </div>

    <div className="hx-stage-wrap"><WorkspacePulse workspace={workspace} onEnter={onEnter} /></div>

    <button className="hx-scroll-cue" onClick={onLearn} aria-label="See how it learns"><span>SCROLL TO SEE HOW IT LEARNS</span><ArrowDown size={14} /></button>
  </section>;
}

