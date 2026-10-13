import React, { useState } from 'react';
import glyphs from './glyphs';

export function DotText({ text, className = '', as: Tag = 'span', dots = true }) {
  const lines = text.toUpperCase().split('|');
  const width = Math.max(...lines.map(line => line.length)) * 6 - 1;
  return <Tag className={`dot-text ${className}`} aria-label={text.replaceAll('|', ' ')}>
    <svg viewBox={`0 0 ${width} ${lines.length * 9 - 2}`} fill="currentColor" aria-hidden="true">
      {lines.flatMap((line, row) => [...line].flatMap((letter, col) => (glyphs[letter] || glyphs[' ']).flatMap((bits, y) => [...bits].map((bit, x) => bit === '1' && (dots
        ? <circle key={`${row}-${col}-${x}-${y}`} cx={col * 6 + x + .5} cy={row * 9 + y + .5} r=".31" />
        : <rect key={`${row}-${col}-${x}-${y}`} x={col * 6 + x} y={row * 9 + y} width=".87" height=".87" />)))))}
    </svg>
  </Tag>;
}

const sprites = {
  byte: [
    '.......BB.......','.......BL.......','......DDDD......','...DDDBBBDDDD...','..DBBBBBBBBBBD..',
    '..DBLLLLLLLBBD..','.DDBDDDDDDDBBDD.','DBBDDEEDDEEDDBBD','DBBDDEEDDEEDDBBD','DBBDDDDDDDDDBBBD',
    '.DDBDDLLLDDDBDD.','..DBBBBBBBBBBD..','...DDDDDDDDDD...','....DBD..DBD....','...DDDD..DDDD...','................',
  ],
  patch: [
    '.......LL.......','......LBBL......','.....LBBBBL.....','....LBBBBBBL....','...LBBBDDBBBL...',
    '..LBBBBDDBBBBL..','.LBBBEBDDBEBBBL.','LBBBBEBDDBEBBBBL','.LBBBBDDDDBBBBL.','..LBBBBBBBBBBL..',
    '...LBBBLLBBBL...','....LBBBBBBL....','.....LBBBBL.....','......LBBL......','.......DD.......','................',
  ],
  scout: [
    '................','..LL........LL..','...BL......LB...','....BLLLLLB.....','...LBBBBBBBL....',
    '..LBBBBBBBBBL...','.DBBDEBDDDEBBD..','DBBBDEBDDDEBBBD.','.DBBDDDDDDDBBD..','..LBBBBBBBBBL...',
    '...LBBBLBBBL....','....LBL.LBL.....','.....D...D......','....L.....L.....','................','................',
  ],
};
const palettes = {
  byte: { B: '#6ce0ca', L: '#b7ffeb', D: '#254d4b', E: '#effff8' },
  patch: { B: '#e9b873', L: '#ffdf9e', D: '#6a5134', E: '#fff6df' },
  scout: { B: '#7daae3', L: '#c2dfff', D: '#344c72', E: '#fff6df' },
};

export function PixelSprite({ kind = 'byte', mode = 'pixel', className = '', interactive = false, onPoke, title }) {
  const [poked, setPoked] = useState(false);
  const sprite = sprites[kind];
  const palette = palettes[kind];
  const cells = sprite.flatMap((row, y) => [...row].map((color, x) => color !== '.' ? { x, y, color } : null).filter(Boolean));
  const poke = () => { setPoked(true); onPoke?.(); setTimeout(() => setPoked(false), 650); };
  const Shape = interactive ? 'button' : 'div';
  return <Shape className={`pixel-sprite ${kind} ${mode} ${poked ? 'poked' : ''} ${className}`} onClick={interactive ? poke : undefined} aria-label={interactive ? title || `Say hello to ${kind}` : undefined} type={interactive ? 'button' : undefined}>
    <svg viewBox={mode === 'voxel' ? '-3 -2 22 21' : '-1 -1 18 18'} shapeRendering={mode === 'dots' ? 'auto' : 'crispEdges'} aria-hidden="true">
      {mode === 'voxel' && [2, 1.5, 1, .5].map(offset => <g key={offset} transform={`translate(${-offset} ${offset})`} fill="#34313e">{cells.map(({ x, y }) => <rect key={`${x}-${y}`} x={x} y={y} width="1.05" height="1.05" />)}</g>)}
      {cells.map(({ x, y, color }) => mode === 'dots' ? <circle key={`${x}-${y}`} cx={x + .5} cy={y + .5} r=".42" fill={palette[color]} className={color === 'E' ? 'sprite-eye' : ''} /> : <rect key={`${x}-${y}`} x={x} y={y} width="1.01" height="1.01" fill={palette[color]} className={color === 'E' ? 'sprite-eye' : ''} />)}
    </svg>
  </Shape>;
}

export function PixelSpark({ className = '' }) { return <svg className={`pixel-spark ${className}`} viewBox="0 0 9 9" fill="currentColor" aria-hidden="true"><path d="M4 0h1v3h1v1h3v1H6v1H5v3H4V6H3V5H0V4h3V3h1z" /></svg>; }

export function MiniBars({ color = 'lime', count = 17 }) { return <div className={`mini-bars ${color}`} aria-hidden="true">{Array.from({ length: count }, (_, i) => <i key={i} style={{ '--bar-height': `${[35, 55, 42, 75, 50, 90, 65, 78, 95, 70, 85, 100, 80, 93, 62, 85, 100][i % 17]}%`, '--i': i }} />)}</div>; }
