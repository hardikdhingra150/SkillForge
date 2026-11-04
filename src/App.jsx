import React, {
  useEffect,
  useRef,
  useState,
} from 'react';

import {
  ArrowUpRight,
  AudioLines,
  ChevronRight,
  Menu,
  Moon,
  Sun,
  Pause,
  Play,
  Search,
  ShieldCheck,
  Terminal,
  X,
} from 'lucide-react';

import {
  DotText,
  PixelSpark,
  PixelSprite,
} from './components/PixelArt';

import {
  crew,
  initialRuns,
  initialSkills,
  stages,
} from './data';

import Landing, {
  EvolvingCore,
} from './components/Landing';

import LivingBackground from './components/LivingBackground';
import CursorCompanions from './components/CursorCompanions';
import MotionVisibility from './components/MotionVisibility';
import MotionText from './components/MotionText';
import ScrollChoreographer from './components/ScrollChoreographer';

import {
  ScrollProgress,
} from './components/ScrollStory';

import SkillForgeProcessView from './components/SkillForgeProcessView.jsx';
import { Button, PageHeading, PanelTop, Status } from './components/ui.jsx';
import { Metrics } from './components/Metrics.jsx';
import { SkillCard } from './components/SkillCard.jsx';
import { CrewPanel } from './components/CrewPanel.jsx';
import { Console } from './components/Console.jsx';
import { useLiveRun } from './state/useLiveRun.js';
import { Modal } from './components/Modal.jsx';
import { SkillDetail } from './components/SkillDetail.jsx';
import { Guardrails } from './routes/Guardrails.jsx';
import { VIEW_IDS, views } from './navigation.js';
import { getMetricsSummary } from './api/skillforgeProcess.js';
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
  const [metricsSummary, setMetricsSummary] = useState(null);

  // Real metrics while the Workbench is open; the sample cards stay when the API is offline.
  useEffect(() => {
    if (view !== 'workbench') {
      return undefined;
    }

    const controller = new AbortController();

    const load = () => getMetricsSummary(controller.signal)
      .then(setMetricsSummary)
      .catch(() => {});

    load();

    const timer = setInterval(load, 20000);

    return () => {
      clearInterval(timer);
      controller.abort();
    };
  }, [view]);
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
  const consoleRef = useRef();

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

  const landingNav = [
    {
      id: 'how',
      label: 'How it learns',
    },
    {
      id: 'trust',
      label: 'Guardrails',
    },
    {
      id: 'start',
      label: 'Get started',
    },
  ];

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
        <header className="topbar">
          <div className="topbar-inner">
            <button
              className="brand"
              onClick={() => navigate('landing')}
              aria-label="SkillForge home"
            >
              <span className="brand-symbol">
                S
                <span />
              </span>

              <DotText text="SKILLFORGE" />

              <span className="brand-beta">
                WORKSPACE
              </span>
            </button>

            <nav
              className={mobileNav ? 'open' : ''}
              aria-label="Main navigation"
            >
              {view === 'landing'
                ? landingNav.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => {
                        scrollLanding(item.id);
                      }}
                    >
                      {item.label}
                    </button>
                  ))
                : views.map((item) => (
                    <button
                      key={item.id}
                      className={
                        view === item.id ? 'active' : ''
                      }
                      onClick={() => {
                        navigate(item.id);
                      }}
                    >
                      <item.icon size={14} />
                      {item.label}

                      {item.id === 'console'
                        && running
                        && (
                          <i className="running-dot" />
                        )}
                    </button>
                  ))}
            </nav>

            <div className="header-actions">
              {view !== 'landing' && (
                <button
                  className="icon-button search-button"
                  aria-label="Search workspace"
                  onClick={() => {
                    setSearch('');
                    setModal({ type: 'search' });
                  }}
                >
                  <Search size={16} />
                  <kbd>⌘K</kbd>
                </button>
              )}

              <button
                className="icon-button theme-button"
                aria-label={`Switch to ${
                  theme === 'dark' ? 'light' : 'dark'
                } mode`}
                onClick={() => {
                  setTheme((value) => (
                    value === 'dark'
                      ? 'light'
                      : 'dark'
                  ));
                }}
              >
                {theme === 'dark'
                  ? <Sun size={16} />
                  : <Moon size={16} />}
              </button>

              <button
                className={`icon-button motion-button ${
                  motion ? 'on' : ''
                }`}
                aria-label={
                  motion
                    ? 'Pause animations'
                    : 'Resume animations'
                }
                aria-pressed={!motion}
                onClick={() => {
                  setMotion((value) => !value);
                }}
              >
                {motion
                  ? <AudioLines size={17} />
                  : <Pause size={17} />}
              </button>

              {view === 'landing' ? (
                <button
                  className="header-enter"
                  onClick={() => navigate('workbench')}
                >
                  Open workspace
                  <ArrowUpRight size={14} />
                </button>
              ) : (
                <button
                  className="profile-avatar"
                  onClick={() => {
                    setModal({ type: 'runtime' });
                  }}
                  aria-label="Workspace details"
                >
                  H
                  <span />
                </button>
              )}

              <button
                className="icon-button mobile-menu"
                aria-label="Toggle navigation"
                aria-expanded={mobileNav}
                onClick={() => {
                  setMobileNav((value) => !value);
                }}
              >
                {mobileNav
                  ? <X size={18} />
                  : <Menu size={18} />}
              </button>
            </div>
          </div>
        </header>

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
              <>
                <section className="hero">
                  <div className="hero-copy">
                    <div className="hero-kicker">
                      <span className="kicker-line" />

                      A WORKSPACE THAT GROWS WITH YOU

                      <PixelSpark />
                    </div>

                    <h1>
                      <DotText text="ALWAYS EVOLVING." />

                      <MotionText
                        text="Your next idea, unlocked."
                      />
                    </h1>

                    <p>
                      Give your agents a task. Let them discover,
                      build, and repair
                      <br className="desktop-break" />
                      {' '}
                      the skills to do it.
                      {' '}
                      <strong>
                        Every run leaves them a little smarter.
                      </strong>
                    </p>

                    <div className="hero-actions">
                      <Button
                        className="lime"
                        icon={Play}
                        onClick={() => {
                          consoleRef.current?.scrollIntoView({
                            behavior: motion
                              ? 'smooth'
                              : 'auto',
                            block: 'center',
                          });

                          startRun();
                        }}
                        disabled={running}
                      >
                        {running
                          ? 'The crew is on it...'
                          : 'Let’s make something happen'}
                      </Button>

                      <button
                        className="quiet-button"
                        onClick={() => {
                          setModal({ type: 'lifecycle' });
                        }}
                      >
                        How it works
                        <ArrowUpRight size={15} />
                      </button>
                    </div>

                    <div className="hero-bottom">
                      <div className="tiny-crew">
                        {crew.map((member) => (
                          <PixelSprite
                            kind={member.kind}
                            key={member.kind}
                          />
                        ))}
                      </div>

                      <span>
                        SMALL TEAM. NEVER-ENDING POTENTIAL.
                      </span>

                      <span className="hero-arrow">
                        ↝
                      </span>
                    </div>
                  </div>

                  <EvolvingCore
                    compact
                    running={running}
                    onInteract={() => {
                      notify(
                        'The forge is listening. Give it a task to learn from.',
                      );
                    }}
                  />
                </section>

                <SkillForgeProcessView
                  requestedExecutionId={requestedExecutionId}
                  onOpenRequestHandled={setRequestedExecutionId}
                />

                <div className="section-meta">
                  <span>
                    <i />
                    {' '}
                    A LITTLE MOMENTUM
                  </span>

                  <span>
                    {metricsSummary
                      ? 'LIVE · FROM YOUR RECORDED RUNS'
                      : 'DEMO WORKSPACE · SAMPLE METRICS'}
                  </span>
                </div>

                <Metrics
                  skills={skills}
                  runs={runs}
                  repairs={repairs}
                  summary={metricsSummary}
                />

                <div className="work-grid">
                  <div ref={consoleRef}>
                    <Console {...consoleProps} />
                  </div>

                  <CrewPanel
                    mode={mode}
                    onSelect={(member) => {
                      setModal({
                        type: 'crew',
                        member,
                      });
                    }}
                  />
                </div>

                <section className="skills-section">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">
                        <span className="tiny-block lavender" />
                        YOUR GROWING COLLECTION
                      </p>

                      <h2>
                        Learn it once.
                        {' '}
                        <span>Use it forever.</span>
                      </h2>
                    </div>

                    <Button
                      className="outline small"
                      onClick={() => navigate('library')}
                    >
                      Explore the skill library
                    </Button>
                  </div>

                  <div className="skills-grid">
                    {skills
                      .filter((skill) => !skill.draft)
                      .slice(0, 3)
                      .map((skill, index) => (
                        <SkillCard
                          key={skill.id}
                          skill={skill}
                          onInspect={showSkill}
                          mode={mode}
                          index={index}
                        />
                      ))}
                  </div>
                </section>

                <section className="recent-panel panel motion-panel">
                  <PanelTop label="saved_tasks.log">
                    <button
                      type="button"
                      className="text-link"
                      onClick={() => navigate('activity')}
                    >
                      Open activity
                      <ArrowUpRight size={12} />
                    </button>
                  </PanelTop>

                  <div style={{ padding: '20px' }}>
                    <p>
                      Browse saved task runs, their current
                      status, and recorded results.
                    </p>

                    <Button
                      className="outline small"
                      onClick={() => navigate('activity')}
                    >
                      View task history
                    </Button>
                  </div>
                </section>

                <div className="closing-strip">
                  <PixelSpark />

                  <DotText
                    text="DISCOVER. CREATE. REPAIR. REPEAT."
                  />

                  <PixelSpark />

                  <button
                    onClick={() => navigate('governance')}
                  >
                    <ShieldCheck size={14} />
                    PLAYFUL OUTSIDE. GOVERNED INSIDE.
                    <ArrowUpRight size={13} />
                  </button>
                </div>
              </>
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
              <>
                <PageHeading
                  label="ONE TASK. A WHOLE LEARNING LOOP."
                  title="Let’s see what happens."
                  description="A missing column is not the end of the story. It is where the learning starts."
                />

                <Console
                  {...consoleProps}
                  expanded
                />

                <div className="console-explain">
                  <article>
                    <span>01 / THE PLOT TWIST</span>

                    <h3>
                      Your CSV says “$1,200.50”.
                      <br />
                      The skill expects a plain number.
                    </h3>

                    <p>
                      v1.0.0 fails with BAD_NUMBER. Patch
                      diagnoses it, switches to parse_amount,
                      and proves the fix on the failing input.
                    </p>
                  </article>

                  <article>
                    <span>02 / THE HAPPY ENDING</span>

                    <h3>
                      Every test passes.
                      <br />
                      A better skill stays with you.
                    </h3>

                    <p>
                      v1.1.0 joins the registry. Run the
                      same task again and the worker
                      reuses it with no repair.
                    </p>
                  </article>
                </div>
              </>
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

            <footer className="site-footer">
              <span>
                <i />
                BUILT FOR THE NEXT “WHAT IF?”
              </span>

              <div>
                <button
                  onClick={() => navigate('landing')}
                >
                  Home
                </button>

                <button
                  onClick={() => navigate('governance')}
                >
                  Guardrails
                </button>

                <button
                  onClick={() => {
                    setModal({ type: 'runtime' });
                  }}
                >
                  Under the hood
                  <ArrowUpRight size={11} />
                </button>

                <span>
                  FRONTEND PLAYGROUND / V.03
                </span>
              </div>
            </footer>
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