import React from 'react';
import { DotText } from './PixelArt';

export default function KineticType({ text, dotted = false, className = '' }) {
  return <span className={`kinetic-type ${dotted ? 'dotted' : ''} ${className}`} aria-label={text}>
    {[...text].map((letter, i) => <span className={`kinetic-letter ${letter === ' ' ? 'letter-space' : ''}`} key={`${i}-${letter}`} style={{ '--letter': i, '--lean': `${i % 2 ? 1 : -1}deg` }} aria-hidden="true"><span className="letter-float"><span className="letter-hover">{dotted ? <DotText text={letter} /> : letter === ' ' ? '\u00a0' : letter}</span></span></span>)}
  </span>;
}
