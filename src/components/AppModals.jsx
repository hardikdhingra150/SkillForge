import {
  ArrowUpRight,
  Layers3,
  Search,
  ShieldCheck,
  Terminal,
} from 'lucide-react';

import { BASE } from '../api/skillforgeProcess.js';
import { stages } from '../data';
import { morePages, views } from '../navigation.js';
import { Modal } from './Modal.jsx';
import { PixelSpark } from './PixelArt';
import { ApiTokenForm } from './ApiTokenForm.jsx';
import { getApiToken } from '../api/skillforgeProcess.js';
import { StatusPill } from './WorkspaceParts.jsx';

// The modals opened from App: workspace settings, the learning loop, and search.
export function AppModals({
  modal,
  skills,
  connection,
  onConnectionChanged,
  search,
  onSearch,
  onNavigate,
  onClose,
}) {
  const query = search.trim().toLowerCase();
  const pages = [
    ...views,
    ...morePages.map((page) => ({ ...page, icon: ShieldCheck })),
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

            {getApiToken().startsWith('sfb_') ? (
              <>
                <div className="runtime-account">
                  <div>
                    <span>Workspace</span>
                    <strong>Private to this browser</strong>
                    <small>No sign-in needed. Your tasks, chats and history stay here; another browser or device starts its own workspace.</small>
                  </div>
                </div>
                <details className="runtime-owner">
                  <summary>Site owner? Use your owner key</summary>
                  <p>Your owner key (API_TOKEN) unlocks Claude and Codex in Chat and opens the owner&rsquo;s workspace in this browser.</p>
                  <ApiTokenForm onChange={onConnectionChanged} />
                </details>
              </>
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

      {modal?.type === 'tour' && (
        <Modal
          title="SkillForge in two minutes"
          eyebrow="TOUR · EVERY FEATURE"
          onClose={onClose}
        >
          <div className="modal-body tour-video">
            {/* The tour is recorded from the real app by scripts/record-tour.mjs. */}
            <video src="/tour/skillforge-tour.webm" poster="/tour/poster.jpg" controls autoPlay playsInline preload="metadata">
              Your browser can&rsquo;t play this video. It shows the Studio, spreadsheet tasks, repairs, new skills,
              connecting your own Claude or Codex, the Skills and Models pages, and workspace settings.
            </video>
            <p className="modal-note">
              Studio · spreadsheet tasks · automatic repairs · new skills · your own Claude and Codex · Skills · Models · settings
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
