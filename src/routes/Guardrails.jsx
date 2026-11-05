import {
  FlaskConical,
  GitBranch,
  History,
  LockKeyhole,
  ShieldCheck,
} from 'lucide-react';
import { PixelSprite } from '../components/PixelArt';
import { PageHeading } from '../components/ui.jsx';

export function Guardrails() {
  const rules = [
    {
      icon: LockKeyhole,
      name: 'A small, approved toolkit.',
      text: 'Skills can only use explicitly allowed tools. No raw shell access or surprise capabilities.',
      value: 'ALLOWLIST ENFORCED',
      kind: 'byte',
    },
    {
      icon: FlaskConical,
      name: 'Earn trust with tests.',
      text: 'New and repaired skills must pass their tests before joining your reusable library.',
      value: 'TEST BEFORE TRUST',
      kind: 'patch',
    },
    {
      icon: GitBranch,
      name: 'Learning has boundaries.',
      text: 'Three repair attempts per run. After that, the agent pauses for a human to take a look.',
      value: '3 ATTEMPTS MAX',
      kind: 'scout',
    },
    {
      icon: History,
      name: 'Leave a trail worth following.',
      text: 'Every contract, test, and version stays connected. See what changed and why it worked.',
      value: 'VERSIONED + TRACEABLE',
      kind: 'byte',
    },
  ];

  return (
    <>
      <PageHeading
        label="AUTONOMY WITH A LITTLE COMMON SENSE"
        title="Room to grow. Clear boundaries."
        description="Let your agents explore. Keep a say in how they work."
      />

      <div className="guard-grid">
        {rules.map((rule, index) => (
          <article
            key={rule.name}
            className={`guard-card motion-panel ${rule.kind}`}
            style={{ '--i': index }}
          >
            <rule.icon size={24} />

            <h2>{rule.name}</h2>
            <p>{rule.text}</p>

            <span>
              <i />
              {rule.value}
            </span>

            <PixelSprite kind={rule.kind} />
          </article>
        ))}
      </div>

      <div className="privacy-panel panel">
        <ShieldCheck size={29} />

        <div>
          <h2>Your workspace. Your rules.</h2>

          <p>
            FastAPI for orchestration. PostgreSQL for
            saved tasks, events, and skill versions.
            <br />
            Every page reads from your own API. Skills run in a
            locked sandbox, and every promotion, retire and restore
            is written to the audit trail.
          </p>
        </div>
      </div>
    </>
  );
}
