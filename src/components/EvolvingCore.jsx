import { useState } from 'react';

import { DotText, PixelSprite } from './PixelArt';

export function EvolvingCore({
  compact = false,
  running = false,
  onInteract,
}) {
  const [charge, setCharge] = useState(0);

  const glowId = compact
    ? 'coreGlowSmall'
    : 'coreGlow';

  return (
    <div
      className={`evolving-core ${
        compact ? 'compact' : ''
      } ${running ? 'charged' : ''}`}
    >
      <svg
        className="core-network"
        viewBox="0 0 420 420"
        fill="none"
        aria-hidden="true"
      >
        <defs>
          <radialGradient id={glowId}>
            <stop
              stopColor="currentColor"
              stopOpacity=".14"
            />

            <stop
              offset="1"
              stopColor="currentColor"
              stopOpacity="0"
            />
          </radialGradient>
        </defs>

        <circle
          cx="210"
          cy="210"
          r="200"
          fill={`url(#${glowId})`}
        />

        <g className="core-rings">
          <ellipse
            cx="210"
            cy="210"
            rx="165"
            ry="66"
            transform="rotate(-30 210 210)"
          />

          <ellipse
            cx="210"
            cy="210"
            rx="165"
            ry="66"
            transform="rotate(30 210 210)"
          />

          <ellipse
            cx="210"
            cy="210"
            rx="165"
            ry="66"
            transform="rotate(90 210 210)"
          />
        </g>

        <circle
          className="core-outer-ring"
          cx="210"
          cy="210"
          r="180"
          strokeDasharray="1 12"
        />

        <g className="core-packets">
          <circle
            cx="210"
            cy="45"
            r="3"
          />

          <rect
            x="355"
            y="278"
            width="5"
            height="5"
          />

          <circle
            cx="61"
            cy="286"
            r="3"
          />
        </g>

        <path
          className="core-axis"
          d="M210 16v30m0 328v30M16 210h30m328 0h30"
        />
      </svg>

      <button
        className="core-heart"
        onClick={() => {
          setCharge((value) => value + 1);
          onInteract?.();
        }}
        aria-label="Wake the SkillForge core"
      >
        <span
          key={charge}
          className={charge ? 'core-flash' : ''}
        >
          <DotText text="SF" />
        </span>

        <i />
        <i />
        <i />
      </button>

      <div className="core-caption">
        <span />

        {running
          ? 'CAPABILITY EVOLVING'
          : 'A MEMORY IN THE MAKING'}
      </div>

      <span className="core-coordinate core-c1">
        INPUT / 001
      </span>

      <span className="core-coordinate core-c2">
        LEARN / ∞
      </span>

      <div className="core-node core-n1">
        <PixelSprite kind="byte" />
        <span>create</span>
      </div>

      <div className="core-node core-n2">
        <PixelSprite kind="patch" />
        <span>repair</span>
      </div>

      <div className="core-node core-n3">
        <PixelSprite kind="scout" />
        <span>discover</span>
      </div>
    </div>
  );
}
