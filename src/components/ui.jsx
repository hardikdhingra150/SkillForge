import { ArrowUpRight } from 'lucide-react';

import MotionText from './MotionText';

export function Button({
  children,
  icon: Icon = ArrowUpRight,
  className = '',
  ...props
}) {
  return (
    <button
      className={`button ${className}`}
      {...props}
    >
      {children}
      {Icon && <Icon size={16} />}
    </button>
  );
}

export function PanelTop({
  label,
  children,
  tone = '',
}) {
  return (
    <div className={`panel-top ${tone}`}>
      <span
        className="panel-sigil"
        aria-hidden="true"
      >
        [·]
      </span>

      <span>{label}</span>

      <div className="panel-top-right">
        {children}
      </div>
    </div>
  );
}

export function Status({
  children,
  color = '',
}) {
  return (
    <span className={`status ${color}`}>
      <i />
      {children}
    </span>
  );
}

export function PageHeading({
  label,
  title,
  description,
  children,
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{label}</p>

        <h1>
          <MotionText text={title} />
        </h1>

        <p>{description}</p>
      </div>

      {children}
    </div>
  );
}
