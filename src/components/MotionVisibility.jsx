import { useEffect } from 'react';

const MOTION_ROOTS = [
  '.forge-hero',
  '.cinema-section',
  '.cinema-finale',
  '.lx-section',
  '.lx-finale',
  '.hero',
  '.metrics',
  '.work-grid',
  '.skills-section',
  '.skills-grid',
  '.recent-panel',
  '.activity-panel',
  '.console-panel',
  '.console-explain',
  '.guard-grid',
  '.privacy-panel',
  '.page-heading',
].join(',');

/** Suspend decorative CSS motion outside the viewport without hiding content. */
export default function MotionVisibility({ motion, routeKey }) {
  useEffect(() => {
    const app = document.querySelector('.app');
    if (!app) return undefined;

    const observed = new Set();
    const pending = new Set();
    let frame = 0;
    let needsPruning = false;
    let active = true;

    const syncVisibility = () => {
      app.classList.toggle('motion-document-hidden', document.hidden);
    };
    syncVisibility();
    document.addEventListener('visibilitychange', syncVisibility);

    const intersection = motion && 'IntersectionObserver' in window
      ? new IntersectionObserver((entries) => {
        if (!active) return;
        entries.forEach(({ target, isIntersecting }) => {
          if (observed.has(target)) target.classList.toggle('motion-sleep', !isIntersecting);
        });
      }, { rootMargin: '80px 0px', threshold: 0 })
      : null;

    const observe = (element) => {
      if (!intersection || observed.has(element) || !app.contains(element)) return;
      observed.add(element);
      intersection.observe(element);
    };

    const flush = () => {
      frame = 0;
      if (!active) return;
      if (needsPruning) {
        observed.forEach((element) => {
          if (!app.contains(element)) {
            intersection.unobserve(element);
            element.classList.remove('motion-sleep');
            observed.delete(element);
          }
        });
        needsPruning = false;
      }
      pending.forEach(observe);
      pending.clear();
    };

    let mutations;
    if (intersection) {
      app.querySelectorAll(MOTION_ROOTS).forEach(observe);
      mutations = new MutationObserver((records) => {
        // Inspect only inserted subtrees. Text updates and animation class changes
        // never rescan the page or schedule another frame.
        records.forEach(({ addedNodes, removedNodes }) => {
          addedNodes.forEach((node) => {
            if (node.nodeType !== Node.ELEMENT_NODE) return;
            if (node.matches(MOTION_ROOTS)) pending.add(node);
            node.querySelectorAll(MOTION_ROOTS).forEach((element) => pending.add(element));
          });
          if (removedNodes.length && !needsPruning) {
            needsPruning = [...removedNodes].some((node) => (
              node.nodeType === Node.ELEMENT_NODE && (
                observed.has(node) || [...observed].some((element) => node.contains(element))
              )
            ));
          }
        });
        if ((pending.size || needsPruning) && !frame) frame = requestAnimationFrame(flush);
      });
      mutations.observe(app, { childList: true, subtree: true });
    }

    return () => {
      active = false;
      cancelAnimationFrame(frame);
      mutations?.disconnect();
      intersection?.disconnect();
      document.removeEventListener('visibilitychange', syncVisibility);
      app.classList.remove('motion-document-hidden');
      observed.forEach((element) => element.classList.remove('motion-sleep'));
      observed.clear();
      pending.clear();
    };
  }, [motion, routeKey]);

  return null;
}
