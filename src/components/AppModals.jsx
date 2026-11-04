import {
  ArrowUpRight,
  Search,
  ShieldCheck,
  Terminal,
} from 'lucide-react';

import { stages } from '../data';
import { views } from '../navigation.js';
import { Modal } from './Modal.jsx';
import { PixelSpark, PixelSprite } from './PixelArt';
import { SkillDetail } from './SkillDetail.jsx';
import { Status } from './ui.jsx';

// The modals opened from App: a skill, a crew member, runtime details, the learning loop, and search.
export function AppModals({
  modal,
  mode,
  skills,
  search,
  onSearch,
  onNavigate,
  onShowSkill,
  notify,
  onClose,
}) {
  return (
    <>
      {modal?.type === 'skill' && (
        <SkillDetail
          key={modal.skill.id}
          skill={modal.skill}
          mode={mode}
          onClose={onClose}
        />
      )}

      {modal?.type === 'crew' && (
        <Modal
          eyebrow="MEET YOUR LITTLE TEAM"
          title={
            `${modal.member.name}, ${
              modal.member.role.toLowerCase()
            }.`
          }
          onClose={onClose}
        >
          <div className="modal-body crew-modal">
            <PixelSprite
              kind={modal.member.kind}
              mode={mode}
              interactive
              onPoke={() => {
                notify(
                  modal.member.speech[
                    Math.floor(
                      Math.random()
                      * modal.member.speech.length,
                    )
                  ],
                );
              }}
            />

            <h3>{modal.member.description}</h3>

            <p>
              {modal.member.kind === 'byte'
                ? 'Byte represents skill creation: turning a new task into a candidate with a clear contract and approved tools.'
                : modal.member.kind === 'patch'
                  ? 'Patch represents evaluation and repair: finding what failed, improving the candidate, and earning trust through tests.'
                  : 'Scout represents discovery and reuse: looking through the registry for an existing capability before creating something new.'}
            </p>

            <span className="modal-note">
              Original characters for the SkillForge preview.
              Click to say hello.
            </span>
          </div>
        </Modal>
      )}

      {modal?.type === 'runtime' && (
        <Modal
          title="A simple engine. A lot of possibility."
          eyebrow="UNDER THE HOOD"
          onClose={onClose}
        >
          <div className="modal-body">
            <div className="runtime-banner">
              <Terminal size={22} />

              <div>
                <h3>Local by design.</h3>

                <p>
                  Your intelligence has a place to call home.
                </p>
              </div>

              <Status>LOCAL WORKSPACE</Status>
            </div>

            {[
              [
                'Frontend',
                'React + Vite',
              ],
              [
                'Orchestration',
                'SkillForge Core · FastAPI',
              ],
              [
                'Skill creation & repair',
                'SkillSmith Engine · planned',
              ],
              [
                'AI runtime',
                'Ollama · planned',
              ],
              [
                'Memory & version history',
                'PostgreSQL registry',
              ],
              [
                'Validation',
                'Deterministic checks + unittest',
              ],
            ].map(([label, value]) => (
              <div
                className="runtime-row"
                key={label}
              >
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}

            <p className="modal-note">
              Process View, Activity, and Skill Library connect
              to the local FastAPI backend and PostgreSQL.
              The dashboard metrics and animated console use
              sample data. Model-based skill creation and
              repair are planned.
            </p>
          </div>
        </Modal>
      )}

      {modal?.type === 'lifecycle' && (
        <Modal
          title="One problem. A lasting capability."
          eyebrow="HOW THE LEARNING LOOP WORKS"
          onClose={onClose}
        >
          <div className="modal-body lifecycle-detail">
            {stages.map((name, index) => (
              <div key={name}>
                <span>0{index + 1}</span>

                <div>
                  <h3>{name}</h3>

                  <p>
                    {[
                      'Find a tested skill that already fits the task.',
                      'Build a focused candidate with a clear contract.',
                      'Run the candidate using only approved tools.',
                      'Check the result against expectations and tests.',
                      'Use the failure as feedback. Make a targeted fix.',
                      'Save a tested artifact with a traceable version.',
                      'Let the next matching task benefit from the work.',
                    ][index]}
                  </p>
                </div>

                <PixelSpark />
              </div>
            ))}
          </div>
        </Modal>
      )}

      {modal?.type === 'search' && (
        <Modal
          title="Where are we going?"
          eyebrow="JUMP TO A PAGE OR A SKILL"
          onClose={onClose}
        >
          <div className="modal-body search-modal">
            <label className="search-field">
              <Search size={17} />

              <input
                autoComplete="off"
                value={search}
                onChange={(event) => {
                  onSearch(event.target.value);
                }}
                placeholder="Type a skill or page name..."
                aria-label="Search workspace"
              />
            </label>

            <div className="search-results">
              {[
                ...views,
                {
                  id: 'governance',
                  label: 'Guardrails',
                  icon: ShieldCheck,
                },
              ]
                .filter((item) => (
                  item.label
                    .toLowerCase()
                    .includes(search.toLowerCase())
                ))
                .map((item) => (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                  >
                    <item.icon size={16} />
                    <span>{item.label}</span>
                    <ArrowUpRight size={14} />
                  </button>
                ))}

              {skills
                .filter((skill) => (
                  skill.name
                    .toLowerCase()
                    .includes(search.toLowerCase())
                ))
                .slice(0, 5)
                .map((skill) => (
                  <button
                    key={skill.id}
                    onClick={() => onShowSkill(skill)}
                  >
                    <PixelSprite kind={skill.kind} />

                    <span>{skill.name}</span>

                    <span className="version">
                      v{skill.version}
                    </span>
                  </button>
                ))}

              {![
                ...views,
                {
                  label: 'Guardrails',
                },
              ].some((item) => (
                item.label
                  .toLowerCase()
                  .includes(search.toLowerCase())
              ))
                && !skills.some((skill) => (
                  skill.name
                    .toLowerCase()
                    .includes(search.toLowerCase())
                ))
                && (
                  <p className="empty-search">
                    Nothing here yet. Try another word.
                  </p>
                )}
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
