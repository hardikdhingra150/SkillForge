import React from 'react';

import {
  ArrowUpRight,
  Code2,
  Database,
  FlaskConical,
  GitBranch,
  Layers3,
  LockKeyhole,
  RotateCcw,
} from 'lucide-react';

import {
  DotText,
  PixelSprite,
} from './PixelArt';

import { SectionRail } from './ScrollStory';
import HeroForge, { CountUp } from './HeroForge';

import Pop, {
  Burst,
  PopWords,
  useInView,
} from './Pop';

const chapters = [
  {
    id: 'top',
    label: 'Intro',
  },
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
    label: 'Begin',
  },
];

const moves = [
  {
    n: '01',
    icon: Code2,
    kind: 'byte',
    title: 'Build what’s missing.',
    text: 'No skill for the task? SkillSmith writes a focused one, with a clear contract and approved tools.',
    visual: 'build',
  },
  {
    n: '02',
    icon: GitBranch,
    kind: 'patch',
    title: 'Repair what breaks.',
    text: 'Tests catch the failure. The repair fixes the cause, and every check has to pass again.',
    visual: 'repair',
  },
  {
    n: '03',
    icon: Layers3,
    kind: 'scout',
    title: 'Remember what works.',
    text: 'The passing skill is saved as a new version. The next run starts from it, a step ahead.',
    visual: 'remember',
  },
];

const rules = [
  {
    icon: LockKeyhole,
    label: 'Approved tools only',
  },
  {
    icon: FlaskConical,
    label: 'Tests before trust',
  },
  {
    icon: RotateCcw,
    label: 'Bounded repair budget',
  },
  {
    icon: Database,
    label: 'Every version traced',
  },
];

// How the engine is built, not usage numbers: each one is enforced in the backend.
const stats = [
  {
    value: 7,
    pad: 2,
    label: 'stages in every learning loop',
  },
  {
    value: 100,
    suffix: '%',
    label: 'of saved skills pass their tests first',
  },
  {
    value: 0,
    pad: 2,
    label: 'network access inside the sandbox',
  },
  {
    value: 2,
    pad: 2,
    label: 'automatic repairs before a person reviews',
  },
];

function MoveVisual({ type }) {
  if (type === 'build') {
    return (
      <div
        className="lx-visual lx-build"
        aria-hidden="true"
      >
        <span>
          <b>skill</b> revenue_by_product v1.0.0
        </span>

        <span>{'  tools: read_csv, column, to_decimal'}</span>

        <span>{'  tests: 4 fixtures · contract checks'}</span>

        <i className="lx-caret" />
      </div>
    );
  }

  if (type === 'repair') {
    return (
      <div
        className="lx-visual lx-repair"
        aria-hidden="true"
      >
        <span className="lx-bad">
          − tools.to_decimal("$1,200.50")
        </span>

        <span className="lx-good">
          + tools.parse_amount("$1,200.50")
        </span>

        <div className="lx-checks">
          <i />
          <i />
          <i />
          <b>ALL PASS</b>
        </div>
      </div>
    );
  }

  return (
    <div
      className="lx-visual lx-remember"
      aria-hidden="true"
    >
      <span className="lx-chip">v1.0.0</span>

      <span className="lx-arrow" />

      <span className="lx-chip now">v1.1.0</span>

      <span className="lx-saved">
        SAVED TO REGISTRY
      </span>
    </div>
  );
}

export default function Landing({
  onEnter,
  onSampleRun,
  motion,
  workspace,
  onToast,
  onTour,
}) {
  const goTo = (id) => {
    document.getElementById(id)?.scrollIntoView({
      behavior: motion ? 'smooth' : 'auto',
      block: 'start',
    });
  };

  return (
    <main className="landing landing-v4 landing-final landing-lx">
      <SectionRail
        sections={chapters}
        onJump={goTo}
      />

      <HeroForge
        workspace={workspace}
        onEnter={onEnter}
        onSampleRun={onSampleRun}
        onLearn={() => goTo('how')}
        onToast={onToast}
        onTour={onTour}
      />

      <section
        className="lx-section"
        id="how"
      >
        <Pop className="lx-head">
          <span
            className="lx-label pop"
            style={{ '--i': 0 }}
          >
            <i />
            01 / HOW IT LEARNS
          </span>

          <h2>
            <PopWords
              text="Three moves."
              start={1}
            />

            <br />

            <em>
              <PopWords
                text="One lasting skill."
                start={3}
              />
            </em>
          </h2>
        </Pop>

        <Pop
          className="lx-moves"
          threshold={0.2}
        >
          <span
            className="lx-thread"
            aria-hidden="true"
          />

          {moves.map((move, index) => (
            <article
              key={move.n}
              className="lx-card pop"
              style={{ '--i': index * 2 }}
            >
              <span
                className="lx-pet pop-hop"
                style={{ '--i': index * 2 + 3 }}
              >
                <PixelSprite kind={move.kind} />
                <Burst />
              </span>

              <div className="lx-card-top">
                <span
                  className="lx-icon pop"
                  style={{ '--i': index * 2 + 2 }}
                >
                  <move.icon size={18} />
                </span>

                <span className="lx-num">
                  {move.n}
                </span>
              </div>

              <h3>{move.title}</h3>

              <p>{move.text}</p>

              <MoveVisual type={move.visual} />
            </article>
          ))}
        </Pop>
      </section>

      <section
        className="lx-section lx-trust"
        id="trust"
      >
        <Pop className="lx-head">
          <span
            className="lx-label pop"
            style={{ '--i': 0 }}
          >
            <i />
            02 / FREEDOM WITH A FRAMEWORK
          </span>

          <h2>
            <PopWords
              text="A curious mind."
              start={1}
            />

            <br />

            <em>
              <PopWords
                text="A clear set of rules."
                start={4}
              />
            </em>
          </h2>
        </Pop>

        <Pop className="lx-rules">
          {rules.map((rule, index) => (
            <span
              key={rule.label}
              className="lx-rule pop"
              style={{ '--i': index }}
            >
              <rule.icon size={15} />
              {rule.label}
            </span>
          ))}
        </Pop>

        <Stats motion={motion} />
      </section>

      <Pop
        as="section"
        className="lx-finale"
        id="start"
        threshold={0.3}
      >
        <span
          className="lx-finale-pets"
          aria-hidden="true"
        >
          {['scout', 'byte', 'patch'].map(
            (kind, index) => (
              <span
                key={kind}
                className="pop-hop"
                style={{ '--i': index + 4 }}
              >
                <PixelSprite kind={kind} />
              </span>
            ),
          )}
        </span>

        <Burst className="lx-finale-burst" />

        <span
          className="lx-label pop"
          style={{ '--i': 0 }}
        >
          <i />
          YOUR NEXT IDEA DESERVES A FIRST TRY
        </span>

        <h2>
          <PopWords
            text="Make your agents"
            start={1}
          />

          <br />

          <span
            className="lx-pixel pop"
            style={{ '--i': 4 }}
          >
            a little smarter.
          </span>
        </h2>

        <div
          className="lx-finale-actions pop"
          style={{ '--i': 6 }}
        >
          <button
            className="forge-cta"
            onClick={onEnter}
          >
            Open your workspace
            <ArrowUpRight size={18} />
          </button>

          <button
            className="hx-try"
            onClick={onSampleRun}
          >
            Try it with a sample file
            <ArrowUpRight size={14} />
          </button>
        </div>
      </Pop>

      <footer className="cinema-footer">
        <button
          className="footer-brand"
          onClick={() => goTo('top')}
        >
          <DotText text="SKILLFORGE" />

          <span>
            BUILT FOR THE NEXT “WHAT IF?”
          </span>
        </button>

        <div>
          <span>
            REACT · FASTAPI · POSTGRESQL
          </span>

          <button
            className="footer-workspace"
            onClick={onEnter}
          >
            Open workspace
            <ArrowUpRight size={14} />
          </button>

          <button
            onClick={() => goTo('top')}
            aria-label="Back to top"
          >
            <ArrowUpRight size={20} />
          </button>
        </div>
      </footer>
    </main>
  );
}

function Stats({ motion }) {
  const [ref, inView] = useInView(0.4);

  return (
    <dl
      ref={ref}
      className={`lx-stats pop-scope ${
        inView ? 'is-in' : ''
      }`}
    >
      {stats.map((stat, index) => (
        <div
          key={stat.label}
          className="pop"
          style={{ '--i': index }}
        >
          <dt>{stat.label}</dt>

          <dd>
            <CountUp
              {...stat}
              run={motion && inView}
            />
          </dd>
        </div>
      ))}
    </dl>
  );
}