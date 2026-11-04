import React, {
  useEffect,
  useRef,
  useState,
} from 'react';

import {
  ChevronRight,
  X,
} from 'lucide-react';

import {
  PixelSprite,
} from './components/PixelArt';

import {
  initialRuns,
  initialSkills,
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

import { Guardrails } from './routes/Guardrails.jsx';
import { Topbar } from './components/Topbar.jsx';
import { Footer } from './components/Footer.jsx';
import { Workbench } from './routes/Workbench.jsx';
import { AppModals } from './components/AppModals.jsx';
import { ConsolePage } from './routes/ConsolePage.jsx';
import { VIEW_IDS } from './navigation.js';

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

      <AppModals
        modal={modal}
        mode={mode}
        skills={skills}
        search={search}
        onSearch={setSearch}
        onNavigate={navigate}
        onShowSkill={showSkill}
        notify={notify}
        onClose={() => setModal(null)}
      />
    </div>
  );
}