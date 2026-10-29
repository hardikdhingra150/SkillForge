import { useEffect } from 'react';

/*
 * One scroll director for every route. Elements are tagged by selector, so the
 * existing markup stays untouched: each one waits offstage until it scrolls in,
 * then plays its entrance once. Siblings in the same group enter in sequence.
 */
const REVEALS = [
  // Landing
  // The hero animates on load, not on scroll, so it is never waiting offstage.
  ['.hx-stats > div', 'up'],
  ['.forge-marquee', 'fade'],
  ['.cinema-section-label, .section-meta', 'line'],
  ['.cinema-section h2, .cinema-finale h2', 'mask'],
  ['.idea-layout > div:first-child > p, .idea-layout > div:first-child > .inline-action', 'up'],
  ['.forge-system', 'rise'],
  ['.forge-system > .system-header, .forge-system > .system-unit, .forge-system > .system-connection, .forge-system > .system-memory', 'left'],
  ['.cinema-section-heading > div, .cinema-section-heading > p', 'up'],
  ['.learning-studio', 'rise'],
  ['.studio-steps > button', 'left'],
  ['.application-tabs > button', 'pop'],
  ['.application-panel', 'rise'],
  ['.principle-grid > article', 'flip'],
  ['.foundation-row > span', 'fade'],
  ['.foundation-row > div > span', 'pop'],
  ['.cinema-finale', 'curtain'],
  ['.finale-pet, .cinema-finale > .cinema-label, .cinema-finale > .forge-cta, .finale-note', 'up'],
  ['.cinema-footer', 'up'],
  // Workspace
  ['.workspace-line', 'fade'],
  ['.main-content .hero-copy > *', 'up'],
  ['.main-content .hero > .evolving-core', 'scale'],
  ['.sf-process', 'rise'],
  ['.metrics > *', 'up'],
  ['.work-grid > *', 'rise'],
  ['.skills-section .section-heading', 'up'],
  ['.skills-grid > *', 'up'],
  ['.recent-panel', 'rise'],
  ['.closing-strip', 'scale'],
  ['.page-heading', 'up'],
  ['.console-explain > article', 'up'],
  ['.guard-grid > *', 'flip'],
  ['.privacy-panel', 'rise'],
  ['.sf-registry__header, .sf-registry__filters, .sf-registry__count, .sf-registry__error, .sf-registry__empty, .sf-registry__more', 'up'],
  ['.sf-registry__grid > *', 'up'],
  ['.sf-history__header, .sf-history__filters, .sf-history__error, .sf-history__empty', 'up'],
  ['.sf-history__list > li', 'left'],
  ['.site-footer', 'fade'],
];
const REVEAL_SELECTOR = REVEALS.map(([selector]) => selector).join(',');

// Sections that publish their scroll position as CSS variables for parallax.
const SCENES = '.forge-hero, .cinema-section, .cinema-finale, .main-content > .hero, .page-heading';
const SPOTLIGHT = '.hx-stage, .forge-system, .learning-studio, .application-panel, .principle-grid > article, .forge-capability-strip > div, .metric-card, .skill-card, .guard-card, .panel, .sf-process, .sf-registry__card, .sf-history__item';
const MAGNETIC = '.forge-cta, .header-enter, .button.lime, .hx-try';
const MAX_STAGGER = 9;
const settle = 1400;

const clamp = (value) => Math.min(1, Math.max(0, value));

export default function ScrollChoreographer({ motion, routeKey }) {
  useEffect(() => {
    const app = document.querySelector('.app');
    const root = document.documentElement;
    if (!app) return undefined;

    const fine = window.matchMedia('(pointer: fine)').matches;
    const timers = new Set();
    let frame = 0;
    let alive = true;

    const variantFor = (element) => REVEALS.find(([selector]) => element.matches(selector))?.[1];

    const finish = (element) => {
      element.classList.add('is-revealed');
      const delay = Number.parseFloat(element.style.getPropertyValue('--reveal-delay')) || 0;
      const timer = setTimeout(() => {
        timers.delete(timer);
        // Hand the element back to its own transitions (hover lifts, etc.).
        element.removeAttribute('data-reveal');
        element.classList.remove('is-revealed');
        element.style.removeProperty('--reveal-delay');
      }, settle + delay);
      timers.add(timer);
    };

    const reveals = motion && 'IntersectionObserver' in window
      ? new IntersectionObserver((entries) => {
        entries.forEach(({ target, isIntersecting, boundingClientRect }) => {
          // Anything already scrolled past (e.g. after a jump link) shows at once.
          if (!isIntersecting && boundingClientRect.top > 0) return;
          reveals.unobserve(target);
          finish(target);
        });
      }, { rootMargin: '0px 0px -9% 0px', threshold: 0.12 })
      : null;

    const tag = (element) => {
      if (!reveals || element.dataset.revealSeen) return;
      const variant = variantFor(element);
      if (!variant) return;
      element.dataset.revealSeen = '1';
      const siblings = element.parentElement
        ? [...element.parentElement.children].filter((node) => node.dataset.reveal === variant || node === element)
        : [element];
      const index = Math.min(siblings.indexOf(element), MAX_STAGGER);
      element.style.setProperty('--reveal-delay', `${index * 75}ms`);
      element.dataset.reveal = variant;
      reveals.observe(element);
    };

    const scan = (scope) => {
      if (scope.matches?.(REVEAL_SELECTOR)) tag(scope);
      scope.querySelectorAll?.(REVEAL_SELECTOR).forEach(tag);
    };

    // Scroll-linked values: page progress, and each scene's travel through the viewport.
    const measure = () => {
      frame = 0;
      if (!alive) return;
      const viewport = window.innerHeight || 1;
      const max = root.scrollHeight - viewport;
      root.style.setProperty('--sf-scroll', max > 0 ? clamp(window.scrollY / max).toFixed(4) : '0');
      if (!motion) return;
      app.querySelectorAll(SCENES).forEach((scene) => {
        const box = scene.getBoundingClientRect();
        if (box.bottom < -viewport || box.top > viewport * 2) return;
        // 0 when the scene's top meets the viewport bottom, 1 when its bottom leaves the top.
        scene.style.setProperty('--scene', clamp((viewport - box.top) / (viewport + box.height)).toFixed(4));
        scene.style.setProperty('--scene-out', clamp(-box.top / Math.max(box.height, 1)).toFixed(4));
      });
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(measure); };

    // Cursor light that follows the pointer across cards.
    let lit = null;
    const onPointerMove = (event) => {
      const card = event.target.closest?.(SPOTLIGHT);
      if (lit && lit !== card) lit.classList.remove('is-lit');
      lit = card;
      if (card) {
        const box = card.getBoundingClientRect();
        card.style.setProperty('--mx', `${event.clientX - box.left}px`);
        card.style.setProperty('--my', `${event.clientY - box.top}px`);
        card.classList.add('is-lit');
      }
      const magnet = event.target.closest?.(MAGNETIC);
      if (magnet) {
        const box = magnet.getBoundingClientRect();
        const x = (event.clientX - box.left - box.width / 2) / box.width;
        const y = (event.clientY - box.top - box.height / 2) / box.height;
        magnet.style.translate = `${(x * 8).toFixed(1)}px ${(y * 6).toFixed(1)}px`;
        magnet.classList.add('is-magnetic');
      }
    };
    const onPointerOut = (event) => {
      const magnet = event.target.closest?.(MAGNETIC);
      if (magnet && !magnet.contains(event.relatedTarget)) magnet.style.translate = '';
      if (lit && !lit.contains(event.relatedTarget)) { lit.classList.remove('is-lit'); lit = null; }
    };

    app.classList.toggle('reveal-armed', Boolean(reveals));
    scan(app);
    const mutations = reveals ? new MutationObserver((records) => {
      records.forEach(({ addedNodes }) => addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) scan(node);
      }));
    }) : null;
    mutations?.observe(app, { childList: true, subtree: true });

    measure();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    if (motion && fine) {
      document.addEventListener('pointermove', onPointerMove, { passive: true });
      document.addEventListener('pointerout', onPointerOut, { passive: true });
    }

    return () => {
      alive = false;
      cancelAnimationFrame(frame);
      mutations?.disconnect();
      reveals?.disconnect();
      timers.forEach(clearTimeout);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
      document.removeEventListener('pointermove', onPointerMove);
      document.removeEventListener('pointerout', onPointerOut);
      app.classList.remove('reveal-armed');
      app.querySelectorAll('[data-reveal-seen]').forEach((element) => {
        element.removeAttribute('data-reveal');
        element.removeAttribute('data-reveal-seen');
        element.classList.remove('is-revealed');
        element.style.removeProperty('--reveal-delay');
      });
      app.querySelectorAll(MAGNETIC).forEach((element) => { element.style.translate = ''; });
      lit?.classList.remove('is-lit');
    };
  }, [motion, routeKey]);

  return null;
}
