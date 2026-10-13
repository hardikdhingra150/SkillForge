import { useEffect, useRef } from 'react';
import { PixelSprite } from './PixelArt';
import './cursor-companions.css';

/** Visible companions that perch until an actual pointer invites them along. */
export default function CursorCompanions({ motion, enabled = true }) {
  const rootRef = useRef(null);
  const byteRef = useRef(null);
  const scoutRef = useRef(null);
  const motionRef = useRef(motion);
  const updateMotionRef = useRef(null);

  useEffect(() => {
    motionRef.current = motion;
    updateMotionRef.current?.();
  }, [motion]);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || !enabled) return;
    const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const pets = [byteRef.current, scoutRef.current];
    const points = [{ x: 0, y: 0 }, { x: 0, y: 0 }];
    const cursor = { x: 0, y: 0, direction: 1 };
    let frame = 0;
    let sparkleFrame = 0;
    let clickTimer;
    let previousTime = 0;
    let lastMove = 0;
    let following = false;
    let mouseSeen = false;
    let focused = document.hasFocus();
    let viewportWidth = window.innerWidth;
    let viewportHeight = window.innerHeight;

    const perch = (index) => ({ x: Math.max(12, viewportWidth - (index ? 154 : 89)), y: Math.max(12, viewportHeight - (index ? 112 : 125)) });
    const draw = (index, bob = 0, tilt = 0) => {
      const point = points[index];
      pets[index].style.transform = `translate3d(${point.x.toFixed(2)}px, ${(point.y + bob).toFixed(2)}px, 0) rotate(${tilt.toFixed(2)}deg)`;
    };
    const putOnPerch = () => {
      points.forEach((point, index) => { Object.assign(point, perch(index)); draw(index); });
      root.classList.add('is-perched', 'is-idle');
      root.classList.remove('is-following');
    };
    const canAnimate = () => motionRef.current && !reducedMotion.matches && !document.hidden;
    const stop = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      previousTime = 0;
      cancelAnimationFrame(sparkleFrame);
      clearTimeout(clickTimer);
      root.classList.remove('is-celebrating');
    };
    const render = (time) => {
      frame = 0;
      if (!canAnimate()) return;
      const delta = Math.min((time - (previousTime || time - 16.67)) / 16.67, 3);
      previousTime = time;
      const idle = !following || time - lastMove > 1500;
      root.classList.toggle('is-idle', idle);
      const verticalOffset = cursor.y > viewportHeight - 155 ? -85 : 37;
      let settled = true;
      points.forEach((point, index) => {
        const previous = points[index - 1];
        const target = following ? {
          x: Math.max(12, Math.min(viewportWidth - 71, (previous?.x ?? cursor.x) - cursor.direction * (index ? 57 : 44))),
          y: Math.max(12, Math.min(viewportHeight - 90, index ? previous.y + 13 : cursor.y + verticalOffset)),
        } : perch(index);
        const dx = target.x - point.x;
        const dy = target.y - point.y;
        if (Math.abs(dx) + Math.abs(dy) > .5) settled = false;
        const smoothing = 1 - Math.pow(index ? .86 : .8, delta);
        point.x += dx * smoothing;
        point.y += dy * smoothing;
        const bob = focused && (finePointer.matches || mouseSeen) ? Math.sin(time / (idle ? 720 : 190) + index * 1.7) * (idle ? 3 : 3.5) : 0;
        draw(index, bob, Math.max(-9, Math.min(9, dx * .12)));
      });
      // A blurred window or touch-only device needs no perpetual animation loop.
      if ((!focused || (!finePointer.matches && !mouseSeen)) && settled) {
        points.forEach((point, index) => draw(index));
        previousTime = 0;
        return;
      }
      frame = requestAnimationFrame(render);
    };
    const start = () => { if (!frame && canAnimate()) frame = requestAnimationFrame(render); };
    const refreshMotion = () => {
      root.classList.toggle('is-paused', !motionRef.current || reducedMotion.matches);
      if (!canAnimate()) {
        stop();
        if (reducedMotion.matches) { following = false; putOnPerch(); }
        return;
      }
      start();
    };
    const move = (event) => {
      if (event.pointerType && event.pointerType !== 'mouse' && event.pointerType !== 'pen') return;
      // Trust a real mouse event even when an embedded browser reports no hover support.
      mouseSeen = true;
      focused = true;
      if (!canAnimate()) return;
      const movementX = event.clientX - cursor.x;
      if (Math.abs(movementX) > 2) cursor.direction = movementX > 0 ? 1 : -1;
      cursor.x = event.clientX;
      cursor.y = event.clientY;
      lastMove = performance.now();
      following = true;
      root.classList.add('is-following');
      root.classList.remove('is-perched', 'is-idle');
      start();
    };
    const celebrate = (event) => {
      if (!canAnimate() || (event.pointerType && event.pointerType !== 'mouse' && event.pointerType !== 'pen')) return;
      root.classList.remove('is-celebrating');
      cancelAnimationFrame(sparkleFrame);
      sparkleFrame = requestAnimationFrame(() => root.classList.add('is-celebrating'));
      clearTimeout(clickTimer);
      clickTimer = setTimeout(() => root.classList.remove('is-celebrating'), 650);
    };
    const returnToPerch = () => {
      following = false;
      root.classList.add('is-perched', 'is-idle');
      root.classList.remove('is-following');
      if (canAnimate()) start();
      else putOnPerch();
    };
    const blur = () => { focused = false; returnToPerch(); };
    const focus = () => { focused = true; start(); };
    const visibility = () => {
      if (document.hidden) { stop(); following = false; putOnPerch(); }
      else { focused = document.hasFocus(); start(); }
    };
    const resize = () => {
      viewportWidth = window.innerWidth;
      viewportHeight = window.innerHeight;
      if (!canAnimate()) putOnPerch();
      else start();
    };
    const pointerPreference = () => { if (!finePointer.matches) returnToPerch(); refreshMotion(); };

    // Always show the mascots on mount, without waiting for a hover event.
    putOnPerch();
    updateMotionRef.current = refreshMotion;
    refreshMotion();
    window.addEventListener('pointermove', move, { passive: true });
    window.addEventListener('pointerdown', celebrate, { passive: true });
    document.documentElement.addEventListener('pointerleave', returnToPerch);
    window.addEventListener('blur', blur);
    window.addEventListener('focus', focus);
    window.addEventListener('resize', resize, { passive: true });
    document.addEventListener('visibilitychange', visibility);
    finePointer.addEventListener('change', pointerPreference);
    reducedMotion.addEventListener('change', refreshMotion);
    return () => {
      stop();
      updateMotionRef.current = null;
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerdown', celebrate);
      document.documentElement.removeEventListener('pointerleave', returnToPerch);
      window.removeEventListener('blur', blur);
      window.removeEventListener('focus', focus);
      window.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', visibility);
      finePointer.removeEventListener('change', pointerPreference);
      reducedMotion.removeEventListener('change', refreshMotion);
    };
  }, [enabled]);

  if (!enabled) return null;
  return <div ref={rootRef} className="cursor-companions is-perched is-idle" aria-hidden="true">
    <div ref={byteRef} className="cursor-companion cursor-companion-byte">
      <PixelSprite kind="byte" />
      <i className="companion-spark" />
    </div>
    <div ref={scoutRef} className="cursor-companion cursor-companion-scout">
      <PixelSprite kind="scout" />
      <i className="companion-spark" />
    </div>
    <div className="companion-whisper">
      <strong>BYTE + SCOUT</strong>
      <span className="companion-pointer-hint">Move your cursor. We’ll follow.</span>
      <span className="companion-touch-hint">Your little forge companions.</span>
    </div>
  </div>;
}
