import {
  ArrowUpRight,
  Layers3,
  LogOut,
  Search,
  ShieldCheck,
  Terminal,
} from 'lucide-react';

import { BASE } from '../api/skillforgeProcess.js';
import { stages } from '../data';
import { views } from '../navigation.js';
import { Modal } from './Modal.jsx';
import { PixelSpark } from './PixelArt';
import { ApiTokenForm } from './ApiTokenForm.jsx';
import { StatusPill } from './WorkspaceParts.jsx';

// The modals opened from App: workspace settings, the learning loop, and search.
export function AppModals({
  modal,
  skills,
  connection,
  onConnectionChanged,
  auth,
  search,
  onSearch,
  onNavigate,
  onClose,
}) {
  const query = search.trim().toLowerCase();
  const pages = [
    ...views,
    {
      id: 'governance',
      label: 'Guardrails',
      icon: ShieldCheck,
    },
  ].filter((item) => item.label.toLowerCase().includes(query));
  const foundSkills = skills
    .filter((skill) => `${skill.skill_id} ${skill.capability}`.toLowerCase().includes(query))
    .slice(0, 5);

  return (
    <>
      {modal?.type === 'runtime' && (
        <Modal
          title="Workspace settings"
          eyebrow="CONNECTION AND ACCESS"
          onClose={onClose}
        >
          <div className="modal-body">
            <div className="runtime-banner">
              <Terminal size={22} />

              <div>
                <h3>Your SkillForge API</h3>

                <p>
                  <code>{BASE}</code>
                </p>
              </div>

              <StatusPill status={connection} />
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
                'SkillSmith · Claude, Codex or a local model',
              ],
              [
                'Model runtime',
                'Claude Code CLI · Codex CLI · Ollama',
              ],
              [
                'Memory & version history',
                'PostgreSQL registry',
              ],
              [
                'Validation',
                'Sandbox, contract checks, cross-model verifier',
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

            {auth?.mode === 'accounts' ? (
              <div className="runtime-account">
                <div>
                  <span>Signed in as</span>
                  <strong>{auth.user ? auth.user.email : 'Nobody yet'}</strong>
                  {auth.user?.workspace && <small>{auth.user.workspace}</small>}
                </div>
                {auth.user && (
                  <button type="button" className="ws-link" onClick={() => { auth.signOut(); onClose(); }}>
                    <LogOut size={13} />
                    Sign out
                  </button>
                )}
              </div>
            ) : (
              <ApiTokenForm onChange={onConnectionChanged} />
            )}

            <p className="modal-note">
              Every page reads from this API and its PostgreSQL database.
              Nothing is pre-recorded: when the API is offline, pages say so
              and show how to start it.
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
                placeholder="Type a page or saved skill..."
                aria-label="Search workspace"
              />
            </label>

            <div className="search-results">
              {pages.map((item) => (
                <button
                  key={item.id}
                  onClick={() => onNavigate(item.id)}
                >
                  <item.icon size={16} />
                  <span>{item.label}</span>
                  <ArrowUpRight size={14} />
                </button>
              ))}

              {foundSkills.map((skill) => (
                <button
                  key={`${skill.skill_id}@${skill.version}`}
                  onClick={() => onNavigate('library')}
                >
                  <Layers3 size={16} />
                  <span>{skill.skill_id}</span>
                  <span className="version">
                    v{skill.version}
                  </span>
                </button>
              ))}

              {!pages.length && !foundSkills.length && (
                <p className="empty-search">
                  Nothing matches. Try another word.
                </p>
              )}
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
