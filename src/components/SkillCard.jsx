import { ArrowUpRight } from 'lucide-react';
import MotionText from './MotionText';
import { PixelSpark, PixelSprite } from './PixelArt';

export function SkillCard({
  skill,
  onInspect,
  mode,
  index = 0,
}) {
  return (
    <button
      className={`skill-card ${skill.kind} motion-panel`}
      style={{ '--i': index }}
      onClick={() => onInspect(skill)}
    >
      <div className="skill-scene">
        <div className="skill-grid" />

        <span className="skill-number">
          SKILL / {String(index + 1).padStart(2, '0')}
        </span>

        <span className="skill-hover-label">
          SAY HELLO ↗
        </span>

        <PixelSprite
          kind={skill.kind}
          mode={mode}
        />

        <div className="skill-platform" />

        <div className="scene-token token-left">
          {skill.category === 'Code'
            ? '</>'
            : skill.category === 'Data'
              ? 'Σ'
              : 'Aa'}
        </div>

        <div className="scene-token token-right">
          {skill.draft ? '...' : '✓'}
        </div>

        <PixelSpark className="skill-spark" />

        <span className="skill-tagline">
          {skill.tag || 'A NEW IDEA TAKING SHAPE'}
        </span>
      </div>

      <div className="skill-content">
        <div className="skill-title">
          <h3>
            <MotionText text={skill.name} />
          </h3>

          <span className="version">
            v{skill.version}
          </span>
        </div>

        <p>{skill.description}</p>

        <div className="skill-tags">
          <span>{skill.category}</span>

          <span>
            {skill.draft
              ? 'Draft'
              : `${skill.tests}/${skill.tests} tests passed`}
          </span>

          <span>{skill.runs} runs</span>
        </div>

        <div className="skill-bottom">
          <code>{skill.id}</code>

          <span>
            Open skill
            <ArrowUpRight size={13} />
          </span>
        </div>
      </div>
    </button>
  );
}
