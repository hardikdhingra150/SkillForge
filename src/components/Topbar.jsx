import {
  ArrowUpRight,
  AudioLines,
  Menu,
  Moon,
  Pause,
  Search,
  Settings2,
  Sun,
  X,
} from 'lucide-react';

import { views } from '../navigation.js';
import { DotText } from './PixelArt';

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

export function Topbar({
  view,
  running,
  theme,
  motion,
  mobileNav,
  onNavigate,
  onScrollLanding,
  onToggleTheme,
  onToggleMotion,
  onToggleNav,
  onSearch,
  onRuntime,
  connection = 'checking',
}) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <button
          className="brand"
          onClick={() => onNavigate('landing')}
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
                    onScrollLanding(item.id);
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
                    onNavigate(item.id);
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
              onClick={onSearch}
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
            onClick={onToggleTheme}
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
            onClick={onToggleMotion}
          >
            {motion
              ? <AudioLines size={17} />
              : <Pause size={17} />}
          </button>

          {view === 'landing' ? (
            <button
              className="header-enter"
              onClick={() => onNavigate('chat')}
            >
              Open Studio
              <ArrowUpRight size={14} />
            </button>
          ) : (
            <button
              className={`profile-avatar ${connection === 'online' ? '' : 'is-off'}`}
              onClick={onRuntime}
              aria-label="Workspace settings"
              title={connection === 'online' ? 'Workspace settings · connected' : 'Workspace settings · not connected'}
            >
              <Settings2 size={15} />
              <span />
            </button>
          )}

          <button
            className="icon-button mobile-menu"
            aria-label="Toggle navigation"
            aria-expanded={mobileNav}
            onClick={onToggleNav}
          >
            {mobileNav
              ? <X size={18} />
              : <Menu size={18} />}
          </button>
        </div>
      </div>
    </header>
  );
}
