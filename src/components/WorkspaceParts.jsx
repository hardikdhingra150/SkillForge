import { useState } from 'react';
import {
  ArrowUpRight,
  Check,
  Copy,
  KeyRound,
  Layers3,
  RefreshCw,
} from 'lucide-react';

import { BASE } from '../api/skillforgeProcess.js';
import { STATUS_LABEL } from '../state/useWorkspace.js';
import { Status } from './ui.jsx';

// Small pieces shared by the workspace home and the landing page. Everything here shows real
// API data, or says plainly that there is none yet.

export function timeAgo(value) {
  const seconds = Math.max(0, (Date.now() - new Date(value).getTime()) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;

  return `${Math.floor(seconds / 86400)} d ago`;
}

const RUN_TONE = {
  succeeded: ['DONE', 'ok'],
  failed: ['FAILED', 'bad'],
  waiting_approval: ['NEEDS REVIEW', 'warn'],
  waiting_input: ['NEEDS INPUT', 'warn'],
  cancelled: ['CANCELLED', ''],
  expired: ['EXPIRED', ''],
  queued: ['QUEUED', 'busy'],
  running: ['RUNNING', 'busy'],
};

export function runTone(status) {
  return RUN_TONE[status] || [status.replaceAll('_', ' ').toUpperCase(), 'busy'];
}

export function StatusPill({ status }) {
  const tone = { online: '', checking: 'peach', locked: 'peach' }[status] ?? 'off';

  return (
    <span className={`ws-pill ${tone}`}>
      <Status color={tone}>{STATUS_LABEL[status]}</Status>
    </span>
  );
}

function CopyCommand({ command }) {
  const [copied, setCopied] = useState(false);

  return (
    <button
      type="button"
      className="ws-command"
      onClick={() => {
        navigator.clipboard?.writeText(command).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1600);
        }, () => {});
      }}
      aria-label={`Copy command: ${command}`}
    >
      <code>{command}</code>
      {copied ? <Check size={13} /> : <Copy size={13} />}
    </button>
  );
}

const SETUP = {
  offline: {
    title: 'Start SkillForge on your machine',
    text: `The page can’t reach the API at ${BASE}. Run these from the project folder, each in its own terminal.`,
    steps: [
      ['Start PostgreSQL', 'make db'],
      ['Create the tables', 'make migrate'],
      ['Start the API', 'make api'],
      ['Start the worker that runs tasks', 'make worker'],
    ],
  },
  degraded: {
    title: 'The database is not answering',
    text: 'The API is up, but PostgreSQL is not. Start it, then refresh.',
    steps: [['Start PostgreSQL', 'make db']],
  },
};

export function SetupSteps({ status, onRetry, onOpenSettings }) {
  if (status === 'locked') {
    return (
      <div className="ws-setup">
        <h3>Add the access token</h3>
        <p>This SkillForge server needs its access token. Paste it in Workspace settings; it stays in this browser.</p>
        <div className="ws-setup-actions">
          <button type="button" className="ws-link" onClick={onOpenSettings}>
            <KeyRound size={13} />
            Add the token
          </button>
        </div>
      </div>
    );
  }

  const setup = SETUP[status];

  if (!setup) return null;

  return (
    <div className="ws-setup">
      <h3>{setup.title}</h3>
      <p>{setup.text}</p>

      <ol>
        {setup.steps.map(([label, command]) => (
          <li key={command}>
            <span>{label}</span>
            <CopyCommand command={command} />
          </li>
        ))}
      </ol>

      <div className="ws-setup-actions">
        <button type="button" className="ws-link" onClick={onRetry}>
          <RefreshCw size={13} />
          Check again
        </button>
      </div>
    </div>
  );
}

export function SavedSkills({ skills, onOpen, limit = 6 }) {
  if (!skills.length) {
    return (
      <p className="ws-empty">
        <Layers3 size={14} />
        No saved skills yet. When a task passes its tests, the skill is saved here.
      </p>
    );
  }

  return (
    <ul className="ws-list">
      {skills.slice(0, limit).map((skill) => {
        const checks = skill.validation?.test_count ?? skill.validation?.tests?.length;

        return (
          <li key={`${skill.skill_id}@${skill.version}`}>
            <button type="button" onClick={onOpen} disabled={!onOpen}>
              <span className="ws-list-main">
                <strong>
                  {skill.skill_id}
                  <em>v{skill.version}</em>
                </strong>
                <small>{skill.contract?.summary || skill.capability}</small>
              </span>
              <span className="ws-chip ok">
                {checks ? `${checks} CHECKS` : 'VALIDATED'}
              </span>
              {onOpen && <ArrowUpRight size={13} aria-hidden="true" />}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
