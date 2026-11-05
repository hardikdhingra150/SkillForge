import { ArrowUpRight, Check, FileUp, Play } from 'lucide-react';

import MotionText from './MotionText';
import { DotText, PixelSpark, PixelSprite } from './PixelArt';
import { Button, PanelTop } from './ui.jsx';
import { RecentRuns, SetupSteps, StatusPill, timeAgo } from './WorkspaceParts.jsx';

// The top of the Workbench: what to do next, and what the workspace really holds.
function steps(workspace) {
  const metrics = workspace.metrics;
  const online = workspace.status === 'online';

  return [
    {
      title: 'Connect the API',
      text: online ? 'SkillForge is running and the database answers.' : 'Start the API and worker on your machine.',
      done: online,
    },
    {
      title: 'Give it a task',
      text: 'Describe what you need in plain words, then attach the CSV it asks for.',
      done: Boolean(metrics?.runs),
    },
    {
      title: 'Get a tested skill',
      text: 'The skill is built or repaired, tested in the sandbox, then saved.',
      done: Boolean(metrics?.skills),
    },
    {
      title: 'Reuse it',
      text: 'The next matching task starts from the saved skill. No repair needed.',
      done: Boolean(metrics?.reuses),
    },
  ];
}

export function WorkspaceHome({
  workspace,
  running,
  onStartTask,
  onSampleRun,
  onOpenRun,
  onOpenSettings,
  onNavigate,
  onHowItWorks,
}) {
  const list = steps(workspace);
  const next = list.findIndex((step) => !step.done);
  const online = workspace.status === 'online';

  return (
    <section className="hero ws-home" aria-labelledby="ws-home-title">
      <div className="hero-copy ws-intro">
        <div className="hero-kicker">
          <span className="kicker-line" />
          YOUR WORKSPACE
          <PixelSpark />
        </div>

        <h1 id="ws-home-title">
          <DotText text={next === -1 ? 'ALL SET.' : 'START HERE.'} />
          <MotionText text="Describe a task. Keep the skill." />
        </h1>

        <p>
          Tell SkillForge what you need. It finds a skill that fits, or builds one,
          tests it in a locked sandbox, repairs it if it breaks, and saves the version
          that works for next time.
        </p>

        <div className="hero-actions ws-actions">
          <Button className="lime" icon={FileUp} onClick={onStartTask} disabled={!online}>
            Start a task
          </Button>

          <button
            type="button"
            className="quiet-button"
            onClick={onSampleRun}
            disabled={running || !online}
          >
            <Play size={14} />
            {running ? 'Sample run in progress…' : 'Try it with a sample file'}
          </button>

          <button type="button" className="quiet-button" onClick={onHowItWorks}>
            How it works
            <ArrowUpRight size={15} />
          </button>
        </div>

        <ol className="ws-steps" aria-label="Getting started">
          {list.map((step, index) => (
            <li
              key={step.title}
              className={step.done ? 'done' : index === next ? 'current' : ''}
            >
              <span className="ws-step-mark" aria-hidden="true">
                {step.done ? <Check size={12} /> : String(index + 1).padStart(2, '0')}
              </span>

              <div>
                <strong>
                  {step.title}
                  <span className="sr-only">{step.done ? ' (done)' : index === next ? ' (next)' : ''}</span>
                </strong>
                <p>{step.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>

      <aside className="ws-status panel motion-panel" aria-label="Workspace status">
        <PanelTop label="workspace_status">
          <StatusPill status={workspace.status} />
        </PanelTop>

        <div className="ws-status-body">
          {online ? (
            <>
              <div className="ws-status-head">
                <PixelSprite kind={running ? 'patch' : 'scout'} />
                <div>
                  <strong>{running ? 'A run is in progress.' : 'Ready for a task.'}</strong>
                  <small>
                    {workspace.metrics?.runs
                      ? `${workspace.metrics.runs} runs · ${workspace.metrics.skills} saved skills`
                      : 'Nothing has run here yet.'}
                  </small>
                </div>
              </div>

              <h2 className="ws-subhead">Latest runs</h2>
              <RecentRuns runs={workspace.runs} onOpen={onOpenRun} />

              <button type="button" className="ws-link" onClick={() => onNavigate('activity')}>
                All activity
                <ArrowUpRight size={13} />
              </button>
            </>
          ) : workspace.status === 'checking' ? (
            <p className="ws-empty">Checking the API…</p>
          ) : (
            <SetupSteps
              status={workspace.status}
              onRetry={workspace.refresh}
              onOpenSettings={onOpenSettings}
            />
          )}
        </div>

        <div className="ws-status-foot">
          <span>{workspace.checkedAt ? `CHECKED ${timeAgo(workspace.checkedAt).toUpperCase()}` : 'CHECKING…'}</span>
          <button type="button" onClick={workspace.refresh}>REFRESH</button>
        </div>
      </aside>
    </section>
  );
}
