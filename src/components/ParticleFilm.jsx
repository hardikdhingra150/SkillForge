import React, { useEffect, useRef } from 'react';

export function ParticleVideo({ motion, className = '', controls = false }) {
  const ref = useRef();
  useEffect(() => {
    const video = ref.current;
    if (!video) return;
    const sync = () => { if (motion && !document.hidden) video.play().catch(() => {}); else video.pause(); };
    sync(); document.addEventListener('visibilitychange', sync);
    return () => { video.pause(); document.removeEventListener('visibilitychange', sync); };
  }, [motion]);
  return <video ref={ref} className={className} autoPlay={motion} muted loop playsInline preload="auto" poster="/video/particle-poster.jpg" controls={controls} aria-label={controls ? 'SkillForge particle film' : undefined} aria-hidden={controls ? undefined : true}><source src="/video/skillforge-particles.mp4" type="video/mp4" /></video>;
}
