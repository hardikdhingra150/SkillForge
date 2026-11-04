import React, {
  useEffect,
  useRef,
  useState,
} from 'react';

import {
  ArrowRight,
  ArrowUpRight,
  AudioLines,
  Check,
  ChevronRight,
  FileText,
  FlaskConical,
  GitBranch,
  History,
  LockKeyhole,
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
import { VIEW_IDS, views } from './navigation.js';
import { getMetricsSummary } from './api/skillforgeProcess.js';
import { LIVE_FILE, replayLines, runLive } from './api/liveRun.js';
import recordedRun from './fixtures/recordedRepairRun.json';
import SkillRegistryView from './components/SkillRegistryView.jsx';
import ExecutionHistory from './components/ExecutionHistory.jsx';
import ChatView from './components/ChatView.jsx';
import ModelsView from './components/ModelsView.jsx';
import ReviewView from './components/ReviewView.jsx';

const sleep = (ms) => (
  new Promise((resolve) => setTimeout(resolve, ms))
);

function LiveResult({ result }) {
  const products = [...(result.products || [])]
    .sort((a, b) => Number(b.revenue) - Number(a.revenue))
    .slice(0, 4);
  const top = Math.max(...products.map((item) => Math.abs(Number(item.revenue))), 1);
  const money = (value) => Number(value).toLocaleString(undefined, {
    style: 'currency',
    currency: 'USD',
  });

  return (
    <div className="demo-result">
      <span>
        <Check size={13} />
        {money(result.total_revenue)} total revenue
        {' · '}
        {result.skill?.id} v{result.skill?.version}
      </span>

      {products.map((item) => (
        <div key={item.product}>
          <b style={{ '--width': `${Math.round((100 * Math.abs(Number(item.revenue))) / top)}%` }} />
          {item.product}
          <em>{money(item.revenue)}</em>
        </div>
      ))}
    </div>
  );
}

function Console({
  logs,
  running,
  runComplete,
  stage,
  reused,
  live = false,
  result = null,
  onRun,
  expanded = false,
}) {
  const logRef = useRef();

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop =
        logRef.current.scrollHeight;
    }
  }, [logs, runComplete]);

  return (
    <section
      className={`console-panel panel motion-panel ${
        expanded ? 'expanded' : ''
      }`}
    >
      <PanelTop label="the_learning_loop.exe">
        <Status color={running ? 'peach' : ''}>
          {running
            ? 'THINKING + TINKERING'
            : runComplete
              ? 'SKILL UNLOCKED'
              : 'READY WHEN YOU ARE'}
        </Status>
      </PanelTop>

      <div className="console-heading">
        <div>
          <p className="eyebrow">
            FAIL A LITTLE. LEARN A LOT.
          </p>

          <h2>
            Watch the magic <span>happen.</span>
          </h2>
        </div>

        <div
          className={`mini-companion ${
            running ? 'busy' : ''
          }`}
        >
          <PixelSprite kind="patch" />
        </div>
      </div>

      <div className="task-input">
        <span className="prompt-caret">›</span>

        <p>
          Analyze my sales CSV. Show revenue by product.
        </p>

        <span className="task-key">↵</span>
      </div>

      <div className="file-chip">
        <FileText size={11} />

        <span>{LIVE_FILE.name}</span>
        <span>{LIVE_FILE.rows} rows · messy amounts</span>
        <span className="demo-text">{live ? 'LIVE' : 'REPLAY'}</span>
      </div>

      <div className="lifecycle">
        {stages.map((name, index) => (
          <div
            key={name}
            className={[
              'lifecycle-step',
              stage === index && running ? 'active' : '',
              runComplete || index < stage ? 'done' : '',
              reused
                && [1, 4, 5].includes(index)
                && stage >= index
                ? 'skipped'
                : '',
            ].filter(Boolean).join(' ')}
          >
            <div className="step-node">
              {runComplete || index < stage
                ? <Check size={11} />
                : <span>{index + 1}</span>}
            </div>

            <span>{name}</span>
          </div>
        ))}
      </div>

      <div
        className="terminal-output"
        ref={logRef}
        aria-live="polite"
        aria-label="Execution log"
      >
        {!logs.length ? (
          <div className="terminal-idle">
            <div className="terminal-symbol">
              {'>_'}
            </div>

            <div>
              <p>
                Every great skill starts with a small problem
                <span className="cursor">_</span>
              </p>

              <span>
                One column mismatch. One clever repair.
                A capability that sticks.
              </span>
            </div>
          </div>
        ) : (
          logs.map((log, index) => (
            <div
              key={index}
              className={`log-line ${log.type || ''}`}
            >
              <span className="log-time">
                {log.time}
              </span>

              <span className="log-tag">
                {log.tag}
              </span>

              <span>{log.message}</span>
            </div>
          ))
        )}

        {runComplete && result && <LiveResult result={result} />}

      </div>

      <div className="console-footer">
        <span>
          <LockKeyhole size={11} />
          {live ? 'REAL RUN · SANDBOXED' : 'RECORDED RUN · API OFFLINE'}
        </span>

        <Button
          className="lime small"
          onClick={onRun}
          disabled={running}
          icon={
            running
              ? AudioLines
              : runComplete
                ? ArrowRight
                : Play
          }
        >
          {running
            ? 'Working on it...'
            : runComplete
              ? (live ? 'Run again · reuse the skill' : 'Replay again')
              : 'Let’s run it'}
        </Button>
      </div>
    </section>
  );
}

function Modal({
  children,
  title,
  eyebrow,
  onClose,
  className = '',
}) {
  const ref = useRef();

  useEffect(() => {
    const before = document.activeElement;
    const previous = document.body.style.overflow;

    document.body.style.overflow = 'hidden';

    const node = ref.current;

    (
      node.querySelector('input')
      || node.querySelector('button')
    )?.focus();

    const handle = (event) => {
      if (event.key === 'Escape') {
        onClose();
      }

      if (event.key === 'Tab') {
        const items = [
          ...node.querySelectorAll(
            'button:not(:disabled),input,textarea,select,[tabindex="0"]',
          ),
        ];

        if (
          event.shiftKey
          && document.activeElement === items[0]
        ) {
          event.preventDefault();
          items.at(-1)?.focus();
        } else if (
          !event.shiftKey
          && document.activeElement === items.at(-1)
        ) {
          event.preventDefault();
          items[0]?.focus();
        }
      }
    };

    document.addEventListener('keydown', handle);

    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener('keydown', handle);
      before?.focus();
    };
    // Mount-only on purpose: the focus trap and scroll lock live for the modal's lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        ref={ref}
        className={`modal ${className}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <div className="modal-header">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h2 id="modal-title">{title}</h2>
          </div>

          <button
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>

        {children}
      </section>
    </div>
  );
}

function SkillDetail({
  skill,
  onClose,
  mode,
}) {
  const [tab, setTab] = useState('Contract');

  const contract = {
    name: skill.id,
    version: skill.version,
    status: skill.draft ? 'draft' : 'validated',

    inputs: skill.id === 'sales_analysis'
      ? {
          csv_path: 'string',
          column_mapping: {
            product: 'Product',
            revenue: 'Sales',
            date: 'OrderDate',
          },
        }
      : {
          source: 'string',
          output_format: 'string',
        },

    allowed_tools: skill.tools,

    validation: skill.draft
      ? 'pending'
      : {
          framework: 'pytest',
          passed: skill.tests,
          total: skill.tests,
        },
  };

  const testNames = skill.id === 'sales_analysis'
    ? [
        'test_column_alias_mapping',
        'test_revenue_aggregation',
        'test_missing_values',
      ]
    : [
        'test_valid_input',
        'test_output_contract',
        'test_missing_values',
        'test_tool_allowlist',
        'test_edge_cases',
        'test_empty_input',
        'test_error_handling',
        'test_consistency',
      ];

  return (
    <Modal
      title={skill.name}
      eyebrow="A CAPABILITY WITH A STORY"
      onClose={onClose}
      className={skill.kind}
    >
      <div className="modal-body">
        <div className="skill-detail-intro">
          <PixelSprite
            kind={skill.kind}
            mode={mode}
          />

          <div>
            <p>{skill.description}</p>

            <span className="version">
              v{skill.version}
            </span>

            <span className="detail-category">
              {skill.category} · {skill.runs} runs
            </span>
          </div>
        </div>

        <div className="detail-tabs">
          {[
            'Contract',
            'Tests',
            'Version history',
          ].map((value) => (
            <button
              key={value}
              className={
                tab === value ? 'selected' : ''
              }
              onClick={() => setTab(value)}
            >
              {value}
            </button>
          ))}
        </div>

        {tab === 'Contract' && (
          <pre className="code-block">
            {JSON.stringify(contract, null, 2)}
          </pre>
        )}

        {tab === 'Tests' && (
          skill.draft ? (
            <div className="empty-state">
              A new idea, waiting for its first test.
              Draft skills are not yet validated.
            </div>
          ) : (
            <>
              <div className="test-list">
                {Array.from(
                  { length: skill.tests },
                  (_, index) => (
                    <div key={index}>
                      <span>{testNames[index]}</span>

                      <span>
                        <Check size={12} />
                        PASSED
                      </span>
                    </div>
                  ),
                )}
              </div>

              <p className="modal-note">
                Illustrative results for this frontend preview.
              </p>
            </>
          )
        )}

        {tab === 'Version history' && (
          <div className="version-history">
            <div>
              <span className="history-node" />

              <span className="version">
                v{skill.version}
              </span>

              <h3>
                {skill.draft
                  ? 'An idea is born.'
                  : 'A little smarter than before.'}
              </h3>

              <p>
                {skill.draft
                  ? 'Created as a local draft. Code generation, tool scoping, and tests come next.'
                  : skill.id === 'sales_analysis'
                    ? 'Mapped revenue → Sales, normalized column aliases, and passed all three checks. Ready to reuse.'
                    : 'Validated the input contract and expected output, then promoted the skill to the registry.'}
              </p>
            </div>

            {!skill.draft && (
              <div>
                <span className="history-node" />
                <span className="version">v1.0</span>

                <h3>Everyone starts somewhere.</h3>

                <p>
                  Created from a task, scoped to approved
                  tools, and sent through evaluation.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}

function Guardrails() {
  const rules = [
    {
      icon: LockKeyhole,
      name: 'A small, approved toolkit.',
      text: 'Skills can only use explicitly allowed tools. No raw shell access or surprise capabilities.',
      value: 'ALLOWLIST ENFORCED',
      kind: 'byte',
    },
    {
      icon: FlaskConical,
      name: 'Earn trust with tests.',
      text: 'New and repaired skills must pass their tests before joining your reusable library.',
      value: 'TEST BEFORE TRUST',
      kind: 'patch',
    },
    {
      icon: GitBranch,
      name: 'Learning has boundaries.',
      text: 'Three repair attempts per run. After that, the agent pauses for a human to take a look.',
      value: '3 ATTEMPTS MAX',
      kind: 'scout',
    },
    {
      icon: History,
      name: 'Leave a trail worth following.',
      text: 'Every contract, test, and version stays connected. See what changed and why it worked.',
      value: 'VERSIONED + TRACEABLE',
      kind: 'byte',
    },
  ];

  return (
    <>
      <PageHeading
        label="AUTONOMY WITH A LITTLE COMMON SENSE"
        title="Room to grow. Clear boundaries."
        description="Let your agents explore. Keep a say in how they work."
      />

      <div className="guard-grid">
        {rules.map((rule, index) => (
          <article
            key={rule.name}
            className={`guard-card motion-panel ${rule.kind}`}
            style={{ '--i': index }}
          >
            <rule.icon size={24} />

            <h2>{rule.name}</h2>
            <p>{rule.text}</p>

            <span>
              <i />
              {rule.value}
            </span>

            <PixelSprite kind={rule.kind} />
          </article>
        ))}
      </div>

      <div className="privacy-panel panel">
        <ShieldCheck size={29} />

        <div>
          <h2>Your workspace. Your rules.</h2>

          <p>
            FastAPI for orchestration. PostgreSQL for
            saved tasks, events, and skill versions.
            <br />
            Process View, Activity, and Skill Library use
            the local backend. The animated console is
            a demo; model-based creation and repair are planned.
          </p>
        </div>
      </div>
    </>
  );
}

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

  const [logs, setLogs] = useState([]);
  const [running, setRunning] = useState(false);
  const [runComplete, setRunComplete] = useState(false);
  const [stage, setStage] = useState(-1);
  const [reused, setReused] = useState(false);
  // The console runs for real against the API; the scripted demo is only a fallback.
  const [consoleLive, setConsoleLive] = useState(true);
  const [liveResult, setLiveResult] = useState(null);
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
  const alive = useRef(true);
  const inFlight = useRef(false);
  const consoleRef = useRef();

  useEffect(() => {
    alive.current = true;

    return () => {
      alive.current = false;
      clearTimeout(toastTimeout.current);
    };
  }, []);

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

  // Offline: replay a recorded real run (src/fixtures/recordedRepairRun.json) at a readable pace.
  const playDemo = async () => {
    if (inFlight.current) {
      return;
    }

    inFlight.current = true;
    setRunning(true);
    setRunComplete(false);
    setReused(false);
    setLiveResult(null);
    setLogs([]);
    setStage(0);

    for (const line of replayLines()) {
      if (!alive.current) {
        return;
      }

      setStage(line.stage);
      setLogs((previous) => [...previous, line]);
      await sleep(line.type === 'error' ? 1400 : 800);
    }

    if (!alive.current) {
      return;
    }

    setLiveResult(recordedRun.result);
    setRunComplete(true);
    setStage(6);
    setRunning(false);
    inFlight.current = false;
    notify('That was a recorded real run. Start the API and worker to run it live.');
  };

  const runController = useRef(null);

  useEffect(() => () => runController.current?.abort(), []);

  const startRun = async () => {
    if (inFlight.current) {
      return;
    }

    inFlight.current = true;

    const started = Date.now();
    const controller = new AbortController();
    let lines = 0;

    runController.current = controller;

    const push = (line) => {
      if (!alive.current) {
        return;
      }

      lines += 1;
      setStage(line.stage);
      setLogs((previous) => [
        ...previous,
        {
          ...line,
          time: `00:${String(Math.floor((Date.now() - started) / 1000)).padStart(2, '0')}`,
        },
      ]);
    };

    setRunning(true);
    setRunComplete(false);
    setReused(false);
    setLiveResult(null);
    setLogs([]);
    setStage(0);

    try {
      const { execution, repaired } = await runLive({
        onLine: push,
        onWaiting: () => push({
          stage: 0,
          tag: 'WAIT',
          type: '',
          message: 'No worker has picked this up yet. Start one with make worker.',
        }),
        signal: controller.signal,
      });

      if (!alive.current) {
        return;
      }

      const ok = execution?.status === 'succeeded';
      const version = execution?.result?.skill?.version;

      setConsoleLive(true);
      setReused(ok && !repaired);
      setLiveResult(ok ? execution.result : null);
      setRunComplete(ok);
      setStage(ok ? 6 : 4);

      if (ok && repaired) {
        setRepairs((value) => value + 1);
      }

      notify(
        !ok
          ? 'The run needs a human. Open Review to retry or reject it.'
          : repaired
            ? `Repaired and saved revenue_by_product v${version}.`
            : `Reused revenue_by_product v${version}. No repair needed.`,
      );
    } catch (error) {
      if (!alive.current || error.name === 'AbortError') {
        return;
      }

      // No API at all: fall back to the scripted demo.
      if (error.status === 0 && !lines) {
        setConsoleLive(false);
        inFlight.current = false;
        setRunning(false);
        await playDemo();
        return;
      }

      push({ stage: 4, tag: 'FAIL', type: 'error', message: error.message });
    } finally {
      if (runController.current === controller) {
        inFlight.current = false;
        setRunning(false);
      }
    }
  };

  const consoleProps = {
    logs,
    running,
    runComplete,
    stage,
    reused,
    live: consoleLive,
    result: liveResult,
    onRun: startRun,
  };

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