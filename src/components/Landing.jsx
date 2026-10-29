import React from 'react';
import { ArrowUpRight, Code2, Database, FlaskConical, GitBranch, Layers3, LockKeyhole, RotateCcw, ShieldCheck } from 'lucide-react';
import { DotText, PixelSprite } from './PixelArt';
import { SectionRail } from './ScrollStory';
import HeroForge, { CountUp } from './HeroForge';
import Pop, { Burst, PopWords, useInView } from './Pop';

export function EvolvingCore({ compact = false, running = false, onInteract }) {
  const [charge, setCharge] = useState(0);
  return <div className={`evolving-core ${compact ? 'compact' : ''} ${running ? 'charged' : ''}`}>
    <svg className="core-network" viewBox="0 0 420 420" fill="none" aria-hidden="true"><defs><radialGradient id={compact ? 'coreGlowSmall' : 'coreGlow'}><stop stopColor="currentColor" stopOpacity=".14" /><stop offset="1" stopColor="currentColor" stopOpacity="0" /></radialGradient></defs><circle cx="210" cy="210" r="200" fill={`url(#${compact ? 'coreGlowSmall' : 'coreGlow'})`} /><g className="core-rings"><ellipse cx="210" cy="210" rx="165" ry="66" transform="rotate(-30 210 210)" /><ellipse cx="210" cy="210" rx="165" ry="66" transform="rotate(30 210 210)" /><ellipse cx="210" cy="210" rx="165" ry="66" transform="rotate(90 210 210)" /></g><circle className="core-outer-ring" cx="210" cy="210" r="180" strokeDasharray="1 12" /><g className="core-packets"><circle cx="210" cy="45" r="3" /><rect x="355" y="278" width="5" height="5" /><circle cx="61" cy="286" r="3" /></g><path className="core-axis" d="M210 16v30m0 328v30M16 210h30m328 0h30" /></svg>
    <button className="core-heart" onClick={() => { setCharge(n => n + 1); onInteract?.(); }} aria-label="Wake the SkillForge core"><span key={charge} className={charge ? 'core-flash' : ''}><DotText text="SF" /></span><i /><i /><i /></button>
    <div className="core-caption"><span />{running ? 'CAPABILITY EVOLVING' : 'A MEMORY IN THE MAKING'}</div>
    <span className="core-coordinate core-c1">INPUT / 001</span><span className="core-coordinate core-c2">LEARN / ∞</span>
    <div className="core-node core-n1"><PixelSprite kind="byte" /><span>create</span></div><div className="core-node core-n2"><PixelSprite kind="patch" /><span>repair</span></div><div className="core-node core-n3"><PixelSprite kind="scout" /><span>discover</span></div>
  </div>;
}

const chapters = [{ id: 'top', label: 'Intro' }, { id: 'how', label: 'How it learns' }, { id: 'trust', label: 'Guardrails' }, { id: 'start', label: 'Begin' }];

const moves = [
  { n: '01', icon: Code2, kind: 'byte', title: 'Build what’s missing.', text: 'No skill for the task? SkillSmith writes a focused one, with a clear contract and approved tools.', visual: 'build' },
  { n: '02', icon: GitBranch, kind: 'patch', title: 'Repair what breaks.', text: 'Tests catch the failure. The repair fixes the cause, and every check has to pass again.', visual: 'repair' },
  { n: '03', icon: Layers3, kind: 'scout', title: 'Remember what works.', text: 'The passing skill is saved as a new version. The next run starts from it, a step ahead.', visual: 'remember' },
];

const rules = [
  { icon: LockKeyhole, label: 'Approved tools only' },
  { icon: FlaskConical, label: 'Tests before trust' },
  { icon: RotateCcw, label: 'Bounded repair budget' },
  { icon: Database, label: 'Every version traced' },
];

const stats = [
  { value: 7, pad: 2, label: 'stages in every learning loop' },
  { value: 100, suffix: '%', label: 'of new skills tested before reuse' },
  { value: 0, pad: 2, label: 'raw shell commands, ever' },
  { display: '∞', label: 'reuses for every solved problem' },
];

function MoveVisual({ type }) {
  if (type === 'build') return <div className="lx-visual lx-build" aria-hidden="true">
    <span><b>def</b> sales_analysis(csv):</span><span>  rows = read_csv(csv)</span><span>  return by_product(rows)</span><i className="lx-caret" />
  </div>;
  if (type === 'repair') return <div className="lx-visual lx-repair" aria-hidden="true">
    <span className="lx-bad">− column = "revenue"</span><span className="lx-good">+ column = "Sales"</span>
    <div className="lx-checks"><i /><i /><i /><b>3 / 3</b></div>
  </div>;
  return <div className="lx-visual lx-remember" aria-hidden="true">
    <span className="lx-chip">v1.0</span><span className="lx-arrow" /><span className="lx-chip now">v1.1</span><span className="lx-saved">SAVED TO REGISTRY</span>
  </div>;
}

export default function Landing({ onEnter, onDemo, motion, onToast }) {
  const goTo = id => document.getElementById(id)?.scrollIntoView({ behavior: motion ? 'smooth' : 'auto', block: 'start' });
  return <main className="landing landing-v4 landing-final landing-lx">
    <SectionRail sections={chapters} onJump={goTo} />
    <HeroForge motion={motion} onEnter={onEnter} onDemo={onDemo} onLearn={() => goTo('how')} onToast={onToast} />

    <section className="lx-section" id="how">
      <Pop className="lx-head">
        <span className="lx-label pop" style={{ '--i': 0 }}><i />01 / HOW IT LEARNS</span>
        <h2><PopWords text="Three moves." start={1} /><br /><em><PopWords text="One lasting skill." start={3} /></em></h2>
      </Pop>
      <Pop className="lx-moves" threshold={0.2}>
        <span className="lx-thread" aria-hidden="true" />
        {moves.map((m, i) => <article key={m.n} className="lx-card pop" style={{ '--i': i * 2 }}>
          <span className="lx-pet pop-hop" style={{ '--i': i * 2 + 3 }}><PixelSprite kind={m.kind} /><Burst /></span>
          <div className="lx-card-top"><span className="lx-icon pop" style={{ '--i': i * 2 + 2 }}><m.icon size={18} /></span><span className="lx-num">{m.n}</span></div>
          <h3>{m.title}</h3>
          <p>{m.text}</p>
          <MoveVisual type={m.visual} />
        </article>)}
      </Pop>
    </section>

    <section className="lx-section lx-trust" id="trust">
      <Pop className="lx-head">
        <span className="lx-label pop" style={{ '--i': 0 }}><i />02 / FREEDOM WITH A FRAMEWORK</span>
        <h2><PopWords text="A curious mind." start={1} /><br /><em><PopWords text="A clear set of rules." start={4} /></em></h2>
      </Pop>
      <Pop className="lx-rules">
        {rules.map((r, i) => <span key={r.label} className="lx-rule pop" style={{ '--i': i }}><r.icon size={15} />{r.label}</span>)}
      </Pop>
      <Stats motion={motion} />
    </section>

    <Pop as="section" className="lx-finale" id="start" threshold={0.3}>
      <span className="lx-finale-pets" aria-hidden="true">{['scout', 'byte', 'patch'].map((k, i) => <span key={k} className="pop-hop" style={{ '--i': i + 4 }}><PixelSprite kind={k} /></span>)}</span>
      <Burst className="lx-finale-burst" />
      <span className="lx-label pop" style={{ '--i': 0 }}><i />YOUR NEXT IDEA DESERVES A FIRST TRY</span>
      <h2><PopWords text="Make your agents" start={1} /><br /><span className="lx-pixel pop" style={{ '--i': 4 }}>a little smarter.</span></h2>
      <div className="lx-finale-actions pop" style={{ '--i': 6 }}>
        <button className="forge-cta" onClick={onEnter}>Open your workspace <ArrowUpRight size={18} /></button>
        <button className="hx-try" onClick={onDemo}>Watch a repair run <ArrowUpRight size={14} /></button>
      </div>
    </Pop>

    <footer className="cinema-footer"><button className="footer-brand" onClick={() => goTo('top')}><DotText text="SKILLFORGE" /><span>BUILT FOR THE NEXT “WHAT IF?”</span></button><div><span>REACT · FASTAPI · SKILLSMITH · OLLAMA · SQLITE</span><button className="footer-workspace" onClick={onEnter}>Open workspace <ArrowUpRight size={14} /></button><button onClick={() => goTo('top')} aria-label="Back to top"><ArrowUpRight size={20} /></button></div></footer>
  </main>;
}

function Stats({ motion }) {
  const [ref, inView] = useInView(0.4);
  return <dl ref={ref} className={`lx-stats pop-scope ${inView ? 'is-in' : ''}`}>
    {stats.map((s, i) => <div key={s.label} className="pop" style={{ '--i': i }}><dt>{s.label}</dt><dd><CountUp {...s} run={motion && inView} /></dd></div>)}
  </dl>;
}
