import { ArrowUpRight } from 'lucide-react';

export function Footer({ onNavigate, onRuntime }) {
  return (
    <footer className="site-footer">
      <span>
        <i />
        BUILT FOR THE NEXT “WHAT IF?”
      </span>

      <div>
        <button
          onClick={() => onNavigate('landing')}
        >
          Home
        </button>

        <button
          onClick={() => onNavigate('governance')}
        >
          Guardrails
        </button>

        <button
          onClick={onRuntime}
        >
          Under the hood
          <ArrowUpRight size={11} />
        </button>

        <span>
          FRONTEND PLAYGROUND / V.03
        </span>
      </div>
    </footer>
  );
}
