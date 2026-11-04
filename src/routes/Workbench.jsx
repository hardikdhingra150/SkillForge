import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Play, ShieldCheck } from 'lucide-react';

import { getMetricsSummary } from '../api/skillforgeProcess.js';
import { crew } from '../data';
import { Console } from '../components/Console.jsx';
import { CrewPanel } from '../components/CrewPanel.jsx';
import { EvolvingCore } from '../components/EvolvingCore.jsx';
import { Metrics } from '../components/Metrics.jsx';
import MotionText from '../components/MotionText';
import { DotText, PixelSpark, PixelSprite } from '../components/PixelArt';
import SkillForgeProcessView from '../components/SkillForgeProcessView.jsx';
import { SkillCard } from '../components/SkillCard.jsx';
import { Button, PanelTop } from '../components/ui.jsx';

export function Workbench({
  running,
  motion,
  mode,
  skills,
  runs,
  repairs,
  consoleProps,
  onRun,
  requestedExecutionId,
  onOpenRequestHandled,
  onNavigate,
  onShowSkill,
  onOpenModal,
  notify,
}) {
  const consoleRef = useRef();
  const [metricsSummary, setMetricsSummary] = useState(null);

  // Real metrics while the Workbench is open; the sample cards stay when the API is offline.
  useEffect(() => {
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
  }, []);

  return (
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

                onRun();
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
                onOpenModal({ type: 'lifecycle' });
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
        onOpenRequestHandled={onOpenRequestHandled}
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
            onOpenModal({
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
            onClick={() => onNavigate('library')}
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
                onInspect={onShowSkill}
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
            onClick={() => onNavigate('activity')}
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
            onClick={() => onNavigate('activity')}
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
