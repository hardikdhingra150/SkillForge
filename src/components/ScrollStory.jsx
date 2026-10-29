import React, { useEffect, useState } from 'react';

/** A hairline across the top bar that fills as the page is read. */
export function ScrollProgress() {
  return <div className="scroll-progress" aria-hidden="true"><i /></div>;
}

/** Chapter rail for the landing page: shows where you are and jumps between sections. */
export function SectionRail({ sections, onJump }) {
  const [active, setActive] = useState(sections[0]?.id);
  useEffect(() => {
    let frame = 0;
    const pick = () => {
      frame = 0;
      const line = window.innerHeight * 0.42;
      let current = sections[0]?.id;
      sections.forEach(({ id }) => {
        const top = document.getElementById(id)?.getBoundingClientRect().top;
        if (top !== undefined && top <= line) current = id;
      });
      setActive(current);
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(pick); };
    pick();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    return () => { cancelAnimationFrame(frame); window.removeEventListener('scroll', schedule); window.removeEventListener('resize', schedule); };
  }, [sections]);
  const index = Math.max(0, sections.findIndex(s => s.id === active));
  return <nav className="section-rail" aria-label="Page sections" style={{ '--rail-index': index, '--rail-count': sections.length }}>
    <span className="section-rail-track" aria-hidden="true"><i /></span>
    {sections.map((s, i) => <button key={s.id} className={s.id === active ? 'active' : ''} aria-current={s.id === active ? 'true' : undefined} onClick={() => onJump(s.id)}>
      <span className="section-rail-index">{String(i).padStart(2, '0')}</span><span className="section-rail-label">{s.label}</span>
    </button>)}
  </nav>;
}
