import {
  CheckCheck,
  GitBranch,
  Layers3,
  Zap,
} from 'lucide-react';
import { MiniBars } from './PixelArt';

export function liveMetrics(summary) {
  const count = (value) => String(value).padStart(2, '0');

  return [
    {
      name: 'Skills in your toolkit',
      value: count(summary.skills),
      sub: 'VALIDATED AND READY',
      icon: Layers3,
      color: 'lime',
    },
    {
      name: 'Successful runs',
      value: summary.success_rate === null ? '—' : String(summary.success_rate),
      unit: summary.success_rate === null ? '' : '%',
      sub: `${summary.succeeded} OF ${summary.runs} RUNS`,
      icon: CheckCheck,
      color: 'lavender',
    },
    {
      name: 'Problems → progress',
      value: count(summary.repairs),
      sub: 'REPAIRED VERSIONS SAVED',
      icon: GitBranch,
      color: 'peach',
    },
    {
      name: 'Skills reused',
      value: count(summary.reuses),
      sub: summary.average_seconds === null
        ? 'NO TIMED RUNS YET'
        : `AVERAGE RUN ${summary.average_seconds < 0.1 ? 'UNDER 0.1' : summary.average_seconds}S`,
      icon: Zap,
      color: 'blue',
    },
  ];
}

const EMPTY = [
  ['Skills in your toolkit', Layers3, 'lime'],
  ['Successful runs', CheckCheck, 'lavender'],
  ['Problems → progress', GitBranch, 'peach'],
  ['Skills reused', Zap, 'blue'],
].map(([name, icon, color]) => ({ name, icon, color, value: '—', sub: 'WAITING FOR THE API' }));

// Real workspace numbers only. Without the API the cards say so instead of guessing.
export function Metrics({ summary }) {
  const metrics = summary ? liveMetrics(summary) : EMPTY;

  return (
    <section
      className="metrics"
      aria-label="Workspace metrics"
    >
      {metrics.map((metric, index) => (
        <article
          className={`metric-card ${metric.color} motion-panel`}
          style={{ '--i': index }}
          key={metric.name}
        >
          <div className="metric-heading">
            <span>{metric.name}</span>
            <metric.icon size={15} />
          </div>

          <div className="metric-main">
            <span
              className="metric-value"
              key={metric.value}
            >
              {metric.value}
              <small>{metric.unit}</small>
            </span>

            <MiniBars
              color={metric.color}
              count={12}
            />
          </div>

          <div className="metric-bottom">
            <span>{metric.sub}</span>
            <span>↗</span>
          </div>
        </article>
      ))}
    </section>
  );
}
