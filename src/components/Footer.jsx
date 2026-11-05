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
          Workspace settings
          <ArrowUpRight size={11} />
        </button>

        <span>
          SKILLFORGE · SELF-HOSTED
        </span>
      </div>
    </footer>
  );
}
