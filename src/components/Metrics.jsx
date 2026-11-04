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

export function Metrics({
  skills,
  repairs,
  summary,
}) {
  const metrics = summary ? liveMetrics(summary) : [

    {
      name: 'Skills in your toolkit',
      value: String(
        skills.filter((skill) => !skill.draft).length,
      ).padStart(2, '0'),
      sub: 'READY FOR THEIR NEXT JOB',
      icon: Layers3,
      color: 'lime',
    },
    {
      name: 'Happy executions',
      value: '98.4',
      unit: '%',
      sub: 'GETTING BETTER WITH EVERY RUN',
      icon: CheckCheck,
      color: 'lavender',
    },
    {
      name: 'Problems → progress',
      value: String(repairs).padStart(2, '0'),
      sub: 'FIXED. TESTED. REMEMBERED.',
      icon: GitBranch,
      color: 'peach',
    },
    {
      name: 'Time back for you',
      value: '4.2',
      unit: 'h',
      sub: 'GO MAKE SOMETHING GOOD',
      icon: Zap,
      color: 'blue',
    },
  ];

  return (
    <section
      className="metrics"
      aria-label={summary ? 'Workspace metrics' : 'Illustrative workspace metrics'}
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
