import { ArrowUpRight } from 'lucide-react';

import { morePages } from '../navigation.js';

export function Footer({ onNavigate, onRuntime }) {
  return (
    <footer className="site-footer">
      <span>
        <i />
        BUILT FOR THE NEXT “WHAT IF?”
      </span>

      <div>
        <button onClick={() => onNavigate('landing')}>Home</button>

        {morePages.map((page) => (
          <button key={page.id} onClick={() => onNavigate(page.id)}>{page.label}</button>
        ))}

        <button onClick={onRuntime}>
          Workspace settings
          <ArrowUpRight size={11} />
        </button>

        <span>SKILLFORGE · SELF-HOSTED</span>
      </div>
    </footer>
  );
}
