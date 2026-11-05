import { useRef } from 'react';
import { ArrowUpRight, ShieldCheck } from 'lucide-react';

import { Console } from '../components/Console.jsx';
import { Metrics } from '../components/Metrics.jsx';
import { DotText, PixelSpark } from '../components/PixelArt';
import SkillForgeProcessView from '../components/SkillForgeProcessView.jsx';
import { PanelTop } from '../components/ui.jsx';
import { WorkspaceHome } from '../components/WorkspaceHome.jsx';
import { SavedSkills } from '../components/WorkspaceParts.jsx';

export function Workbench({
  workspace,
  running,
  motion,
  consoleProps,
  onRun,
  requestedExecutionId,
  onOpenRequestHandled,
  onOpenRun,
  onNavigate,
  onOpenModal,
}) {
  const taskRef = useRef();
  const consoleRef = useRef();
  const behavior = motion ? 'smooth' : 'auto';

  return (
    <>
      <WorkspaceHome
        workspace={workspace}
        running={running}
        onStartTask={() => {
          taskRef.current?.scrollIntoView({ behavior, block: 'start' });
          taskRef.current?.querySelector('textarea')?.focus({ preventScroll: true });
        }}
        onSampleRun={() => {
          consoleRef.current?.scrollIntoView({ behavior, block: 'center' });
          onRun();
        }}
        onOpenRun={onOpenRun}
        onOpenSettings={() => onOpenModal({ type: 'runtime' })}
        onNavigate={onNavigate}
        onHowItWorks={() => onOpenModal({ type: 'lifecycle' })}
      />

      <div className="section-meta">
        <span>
          <i />
          {' '}
          YOUR NUMBERS
        </span>

        <span>
          {workspace.metrics ? 'LIVE · FROM YOUR RECORDED RUNS' : 'SHOWN ONCE THE API IS CONNECTED'}
        </span>
      </div>

      <Metrics summary={workspace.metrics} />

      <div ref={taskRef} className="ws-task-anchor">
        <SkillForgeProcessView
          requestedExecutionId={requestedExecutionId}
          onOpenRequestHandled={onOpenRequestHandled}
          onChanged={workspace.refresh}
        />
      </div>

      <div className="work-grid">
        <div ref={consoleRef}>
          <Console {...consoleProps} />
        </div>

        <section className="ws-skills panel motion-panel" aria-labelledby="ws-skills-title">
          <PanelTop label="skill_registry">
            <button type="button" className="text-link" onClick={() => onNavigate('library')}>
              Open library
              <ArrowUpRight size={12} />
            </button>
          </PanelTop>

          <div className="ws-skills-body">
            <p className="eyebrow">
              <span className="tiny-block lavender" />
              LEARN IT ONCE. USE IT FOREVER.
            </p>

            <h2 id="ws-skills-title">Saved skills</h2>

            {workspace.status === 'online' ? (
              <SavedSkills skills={workspace.skills} onOpen={() => onNavigate('library')} />
            ) : (
              <p className="ws-empty">Your saved skills show up here once the API is connected.</p>
            )}
          </div>
        </section>
      </div>

      <div className="closing-strip">
        <PixelSpark />

        <DotText
          text="DISCOVER. CREATE. REPAIR. REPEAT."
        />

        <PixelSpark />

        <button
          onClick={() => onNavigate('governance')}
        >
          <ShieldCheck size={14} />
          PLAYFUL OUTSIDE. GOVERNED INSIDE.
          <ArrowUpRight size={13} />
        </button>
      </div>
    </>
  );
}
