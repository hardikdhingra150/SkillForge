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

import Landing from './components/Landing';

import LivingBackground from './components/LivingBackground';
import CursorCompanions from './components/CursorCompanions';
import MotionVisibility from './components/MotionVisibility';
import ScrollChoreographer from './components/ScrollChoreographer';

import {
  ScrollProgress,
} from './components/ScrollStory';

import { StatusPill } from './components/WorkspaceParts.jsx';
import { useLiveRun } from './state/useLiveRun.js';
import { useWorkspace } from './state/useWorkspace.js';

import { Guardrails } from './routes/Guardrails.jsx';
import { Topbar } from './components/Topbar.jsx';
import { Footer } from './components/Footer.jsx';
import { Workbench } from './routes/Workbench.jsx';
import { AppModals } from './components/AppModals.jsx';
import { ConsolePage } from './routes/ConsolePage.jsx';
import { PAGE_LABEL, VIEW_IDS } from './navigation.js';

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

  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState('');
  const [search, setSearch] = useState('');

  const workspace = useWorkspace();

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

  // Text the Workbench hands to Chat ("Do this in Chat"); Chat starts with it in the message box.
  const [chatDraft, setChatDraft] = useState('');
  // The home page's "Try it with a sample file": Studio runs the sample once when it opens.
  const [studioSample, setStudioSample] = useState(false);

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
    onFinished: workspace.refresh,
  });

  const openRun = (executionId) => {
    setRequestedExecutionId(executionId);
    navigate('workbench');
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
          connection={workspace.status}
        />

        {view === 'landing' ? (
          <Landing
            motion={motion}
            workspace={workspace}
            onEnter={() => navigate('chat')}
            onSampleRun={() => {
              setStudioSample(true);
              navigate('chat');
            }}
            onToast={notify}
            onTour={() => setModal({ type: 'tour' })}
          />
        ) : (
          <main
            className="main-content"
            key={view}
          >
            <div className="workspace-line">
              <div>
                <span className="tiny-block" />
                SKILLFORGE

                <span className="workspace-divider">
                  /
                </span>

                <span>
                  {(PAGE_LABEL[view] || view).toUpperCase()}
                </span>
              </div>

              <button
                onClick={() => {
                  setModal({ type: 'runtime' });
                }}
                aria-label="Workspace settings and connection"
              >
                <StatusPill status={workspace.status} />
                <ChevronRight size={12} />
              </button>
            </div>

            {view === 'workbench' && (
              <Workbench
                workspace={workspace}
                running={running}
                motion={motion}
                consoleProps={consoleProps}
                onRun={startRun}
                requestedExecutionId={requestedExecutionId}
                onOpenRequestHandled={setRequestedExecutionId}
                onOpenChat={(text) => { setChatDraft(text); navigate('chat'); }}
                onNavigate={navigate}
                onOpenModal={setModal}
              />
            )}

            {view === 'chat' && (
              <ChatView onOpenLibrary={() => navigate('library')} initialDraft={chatDraft} onDraftUsed={() => setChatDraft('')}
                        onTour={() => setModal({ type: 'tour' })}
                        startSample={studioSample} onSampleStarted={() => setStudioSample(false)} />
            )}

            {view === 'models' && <ModelsView onOpenStudio={() => navigate('chat')} />}

            {view === 'review' && (
              <ReviewView onOpenRun={openRun} />
            )}

            {view === 'library' && (
              <SkillRegistryView
                onOpenWorkbench={() => navigate('chat')}
              />
            )}

            {view === 'console' && (
              <ConsolePage consoleProps={consoleProps} />
            )}

            {view === 'activity' && (
              <ExecutionHistory onOpen={openRun} />
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
        skills={workspace.skills}
        connection={workspace.status}
        onConnectionChanged={workspace.refresh}
        search={search}
        onSearch={setSearch}
        onNavigate={navigate}
        onClose={() => setModal(null)}
      />
    </div>
  );
}