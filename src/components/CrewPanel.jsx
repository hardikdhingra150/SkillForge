import { ArrowUpRight } from 'lucide-react';
import { PixelSpark, PixelSprite } from './PixelArt';
import { PanelTop } from './ui.jsx';
import { crew } from '../data';

export function CrewPanel({
  mode,
  onSelect,
}) {
  return (
    <section className="crew-panel panel motion-panel">
      <PanelTop label="your_little_team">
        <span className="crew-count">
          03 ONLINE
        </span>
      </PanelTop>

      <div className="crew-heading">
        <h2>
          Good things come
          <br />
          in little pixels.
        </h2>

        <p>Different talents. One shared mission.</p>
      </div>

      <div className="crew-list">
        {crew.map((member) => (
          <button
            className={`crew-member ${member.kind}`}
            key={member.kind}
            onClick={() => onSelect(member)}
          >
            <div className="crew-avatar">
              <PixelSprite
                kind={member.kind}
                mode={mode}
              />
            </div>

            <div>
              <h3>
                {member.name}
                <span>{member.role}</span>
              </h3>

              <p>{member.description}</p>
            </div>

            <ArrowUpRight size={14} />
          </button>
        ))}
      </div>

      <div className="crew-note">
        <PixelSpark />

        <span>
          PERSONALITY INCLUDED.
          <br />
          CAPABILITIES KEEP GROWING.
        </span>

        <span className="crew-heart">♡</span>
      </div>
    </section>
  );
}
