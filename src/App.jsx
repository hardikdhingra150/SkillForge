import React, {
  useEffect,
  useRef,
  useState,
} from 'react';

import {
  ArrowUpRight,
  ChevronRight,
  Search,
  ShieldCheck,
  Terminal,
  X,
} from 'lucide-react';

import {
  PixelSpark,
  PixelSprite,
} from './components/PixelArt';

import {
  initialRuns,
  initialSkills,
  stages,
} from './data';

import Landing from './components/Landing';

import LivingBackground from './components/LivingBackground';
import CursorCompanions from './components/CursorCompanions';
import MotionVisibility from './components/MotionVisibility';
import ScrollChoreographer from './components/ScrollChoreographer';

import {
  ScrollProgress,
} from './components/ScrollStory';

import { Status } from './components/ui.jsx';
import { useLiveRun } from './state/useLiveRun.js';
import { Modal } from './components/Modal.jsx';
import { SkillDetail } from './components/SkillDetail.jsx';
import { Guardrails } from './routes/Guardrails.jsx';
import { Topbar } from './components/Topbar.jsx';
import { Footer } from './components/Footer.jsx';
import { Workbench } from './routes/Workbench.jsx';
import { ConsolePage } from './routes/ConsolePage.jsx';
import { VIEW_IDS, views } from './navigation.js';

import SkillRegistryView from './components/SkillRegistryView.jsx';
import ExecutionHistory from './components/ExecutionHistory.jsx';
import ChatView from './components/ChatView.jsx';
import ModelsView from './components/ModelsView.jsx';
import ReviewView from './components/ReviewView.jsx';

export default function App() {
  const [
    requestedExecutionId,
    setRequestedExecutionId,
  ] = useState('');

  const [view, setView] = useState(() => (
    VIEW_IDS.includes(location.hash.slice(1))
      ? location.hash.slice(1)
      : 'landing'
  ));

  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('skillforge-theme')
        === 'light'
        ? 'light'
        : 'dark';
    } catch {
      return 'dark';
    }
  });

  const [mobileNav, setMobileNav] = useState(false);

  const scene = 'particle';

  const [motion, setMotion] = useState(() => (
    !window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches
  ));

  const [mode] = useState('voxel');
  const [skills] = useState(initialSkills);
  const [runs] = useState(initialRuns);

  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState('');

  const [repairs, setRepairs] = useState(8);
  const [search, setSearch] = useState('');

  useEffect(() => {
    document.documentElement.dataset.scene = scene;

    try {
      localStorage.setItem('skillforge-scene', scene);
    } catch {}
  }, [scene]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;

    try {
      localStorage.setItem('skillforge-theme', theme);
    } catch {}

    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute(
        'content',
        theme === 'dark' ? '#181818' : '#e9e9e9',
      );
  }, [theme, scene]);

  useEffect(() => {
    const route = () => {
      const id = location.hash.slice(1);

      setView(
        VIEW_IDS.includes(id)
          ? id
          : 'landing',
      );

      setMobileNav(false);
    };

    window.addEventListener('hashchange', route);

    return () => {
      window.removeEventListener('hashchange', route);
    };
  }, []);

  const toastTimeout = useRef();

  useEffect(() => () => clearTimeout(toastTimeout.current), []);

  useEffect(() => {
    const handleShortcut = (event) => {
      if (
        (event.metaKey || event.ctrlKey)
        && event.key.toLowerCase() === 'k'
      ) {
        event.preventDefault();
        setSearch('');
        setModal({ type: 'search' });
      }
    };

    document.addEventListener(
      'keydown',
      handleShortcut,
    );

    return () => {
      document.removeEventListener(
        'keydown',
        handleShortcut,
      );
    };
  }, []);

  const notify = (text) => {
    clearTimeout(toastTimeout.current);
    setToast(text);

    toastTimeout.current = setTimeout(
      () => setToast(''),
      3500,
    );
  };

  const navigate = (next) => {
    history.pushState(
      null,
      '',
      next === 'landing'
        ? location.pathname
        : `#${next}`,
    );

    setView(next);
    setMobileNav(false);
    setModal(null);

    window.scrollTo({
      top: 0,
      behavior: 'instant',
    });
  };

  const { consoleProps, running, startRun } = useLiveRun({
    notify,
    onRepaired: () => setRepairs((value) => value + 1),
  });

  const showSkill = (skill) => {
    setModal({
      type: 'skill',
      skill,
    });
  };

  const scrollLanding = (id) => {
    setMobileNav(false);

    document
      .getElementById(id)
      ?.scrollIntoView({
        behavior: motion ? 'smooth' : 'auto',
      });
  };

  return (
    <div
      data-theme={theme}
      data-scene={scene}
      className={`app ${
        view === 'landing'
          ? 'is-landing'
          : 'is-workspace'
      } ${motion ? '' : 'motion-paused'}`}
    >
      <LivingBackground motion={motion} />

      <CursorCompanions
        motion={motion}
        enabled={!modal}
      />

      <MotionVisibility
        motion={motion}
        routeKey={view}
      />

      <ScrollChoreographer
        motion={motion}
        routeKey={view}
      />

      <ScrollProgress />

      <div
        className="app-content"
        inert={modal ? true : undefined}
      >
        <Topbar
          view={view}
          running={running}
          theme={theme}
          motion={motion}
          mobileNav={mobileNav}
          onNavigate={navigate}
          onScrollLanding={scrollLanding}
          onToggleTheme={() => {
            setTheme((value) => (
              value === 'dark'
                ? 'light'
                : 'dark'
            ));
          }}
          onToggleMotion={() => {
            setMotion((value) => !value);
          }}
          onToggleNav={() => {
            setMobileNav((value) => !value);
          }}
          onSearch={() => {
            setSearch('');
            setModal({ type: 'search' });
          }}
          onRuntime={() => {
            setModal({ type: 'runtime' });
          }}
        />

        {view === 'landing' ? (
          <Landing
            onLibrary={() => navigate('library')}
            motion={motion}
            onEnter={() => navigate('workbench')}
            onDemo={() => {
              navigate('console');
              startRun();
            }}
            onToast={notify}
          />
        ) : (
          <main
            className="main-content"
            key={view}
          >
            <div className="workspace-line">
              <div>
                <span className="tiny-block" />
                HARDIK’S PLAYGROUND

                <span className="workspace-divider">
                  /
                </span>

                <span>
                  {view === 'workbench'
                    ? 'WORKSPACE 001'
                    : view.toUpperCase()}
                </span>
              </div>

              <button
                onClick={() => {
                  setModal({ type: 'runtime' });
                }}
              >
                <Status>LOCAL WORKSPACE</Status>
                <ChevronRight size={12} />
              </button>
            </div>

            {view === 'workbench' && (
              <Workbench
                running={running}
                motion={motion}
                mode={mode}
                skills={skills}
                runs={runs}
                repairs={repairs}
                consoleProps={consoleProps}
                onRun={startRun}
                requestedExecutionId={requestedExecutionId}
                onOpenRequestHandled={setRequestedExecutionId}
                onNavigate={navigate}
                onShowSkill={showSkill}
                onOpenModal={setModal}
                notify={notify}
              />
            )}

            {view === 'chat' && (
              <ChatView onOpenLibrary={() => navigate('library')} />
            )}

            {view === 'models' && <ModelsView />}

            {view === 'review' && (
              <ReviewView onOpenRun={(id) => { setRequestedExecutionId(id); navigate('workbench'); }} />
            )}

            {view === 'library' && (
              <SkillRegistryView
                onOpenWorkbench={() => navigate('workbench')}
              />
            )}

            {view === 'console' && (
              <ConsolePage consoleProps={consoleProps} />
            )}

            {view === 'activity' && (
              <ExecutionHistory
                onOpen={(executionId) => {
                  setRequestedExecutionId(executionId);
                  navigate('workbench');
                }}
              />
            )}

            {view === 'governance' && (
              <Guardrails />
            )}

            <Footer
              onNavigate={navigate}
              onRuntime={() => {
                setModal({ type: 'runtime' });
              }}
            />
          </main>
        )}
      </div>

      {toast && (
        <div
          className="toast"
          role="status"
        >
          <PixelSprite kind="byte" />

          <span>{toast}</span>

          <button
            onClick={() => setToast('')}
            aria-label="Dismiss notification"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {modal?.type === 'skill' && (
        <SkillDetail
          key={modal.skill.id}
          skill={modal.skill}
          mode={mode}
          onClose={() => setModal(null)}
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
          onClose={() => setModal(null)}
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
          onClose={() => setModal(null)}
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
          onClose={() => setModal(null)}
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
          onClose={() => setModal(null)}
        >
          <div className="modal-body search-modal">
            <label className="search-field">
              <Search size={17} />

              <input
                autoComplete="off"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
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
                    onClick={() => navigate(item.id)}
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
                    onClick={() => showSkill(skill)}
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
    </div>
  );
}