import React, { useEffect, useRef, useState } from 'react';

/**
 * A scope that flips to `.is-in` once it scrolls into view. Children marked
 * `.pop` spring in on that flip, staggered by their `--i`.
 */
export function useInView(threshold = 0.25) {
  const ref = useRef();
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const node = ref.current;
    if (!node || !('IntersectionObserver' in window)) { setInView(true); return undefined; }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting || entry.boundingClientRect.top < 0) { setInView(true); observer.disconnect(); }
    }, { threshold, rootMargin: '0px 0px -8% 0px' });
    observer.observe(node);
    return () => observer.disconnect();
  }, [threshold]);
  return [ref, inView];
}

export default function Pop({ as: Tag = 'div', className = '', threshold = 0.25, children, ...rest }) {
  const [ref, inView] = useInView(threshold);
  const [settled, setSettled] = useState(false);
  // Once the entrance has played, drop the stagger so hovers respond at once.
  useEffect(() => {
    if (!inView) return undefined;
    const timer = setTimeout(() => setSettled(true), 1800);
    return () => clearTimeout(timer);
  }, [inView]);
  return <Tag ref={ref} className={`pop-scope ${inView ? 'is-in' : ''} ${settled ? 'is-settled' : ''} ${className}`} {...rest}>{children}</Tag>;
}

/** Splits a line into words that pop in one after another. */
export function PopWords({ text, start = 0, className = '' }) {
  return <span className={className} aria-label={text}>{text.split(' ').map((word, i) => <span key={`${word}-${i}`} aria-hidden="true" className="pop pop-word" style={{ '--i': start + i }}>{word}{' '}</span>)}</span>;
}

/** Eight pixel sparks that fly out from a point when their scope pops in. */
export function Burst({ className = '' }) {
  return <span className={`burst ${className}`} aria-hidden="true">{Array.from({ length: 8 }, (_, i) => <i key={i} style={{ '--a': `${i * 45 + 22}deg` }} />)}</span>;
}
