import { useEffect, useRef } from 'react';
import {
  ArrowRight,
  AudioLines,
  Check,
  FileText,
  LockKeyhole,
  Play,
} from 'lucide-react';
import { LIVE_FILE } from '../api/liveRun.js';
import { PixelSprite } from './PixelArt';
import { Button, PanelTop, Status } from './ui.jsx';
import { stages } from '../data';

export function LiveResult({ result }) {
  const products = [...(result.products || [])]
    .sort((a, b) => Number(b.revenue) - Number(a.revenue))
    .slice(0, 4);
  const top = Math.max(...products.map((item) => Math.abs(Number(item.revenue))), 1);
  const money = (value) => Number(value).toLocaleString(undefined, {
    style: 'currency',
    currency: 'USD',
  });

  return (
    <div className="demo-result">
      <span>
        <Check size={13} />
        {money(result.total_revenue)} total revenue
        {' · '}
        {result.skill?.id} v{result.skill?.version}
      </span>

      {products.map((item) => (
        <div key={item.product}>
          <b style={{ '--width': `${Math.round((100 * Math.abs(Number(item.revenue))) / top)}%` }} />
          {item.product}
          <em>{money(item.revenue)}</em>
        </div>
      ))}
    </div>
  );
}

export function Console({
  logs,
  running,
  runComplete,
  stage,
  reused,
  offline = false,
  result = null,
  onRun,
  expanded = false,
}) {
  const logRef = useRef();

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop =
        logRef.current.scrollHeight;
    }
  }, [logs, runComplete]);

  return (
    <section
      className={`console-panel panel motion-panel ${
        expanded ? 'expanded' : ''
      }`}
    >
      <PanelTop label="the_learning_loop.exe">
        <Status color={running ? 'peach' : ''}>
          {running
            ? 'THINKING + TINKERING'
            : offline
              ? 'API OFFLINE'
              : runComplete
                ? 'SKILL UNLOCKED'
                : 'READY WHEN YOU ARE'}
        </Status>
      </PanelTop>

      <div className="console-heading">
        <div>
          <p className="eyebrow">
            SAMPLE RUN · REAL ENGINE
          </p>

          <h2>
            Watch a repair <span>happen.</span>
          </h2>
        </div>

        <div
          className={`mini-companion ${
            running ? 'busy' : ''
          }`}
        >
          <PixelSprite kind="patch" />
        </div>
      </div>

      <div className="task-input">
        <span className="prompt-caret">›</span>

        <p>
          Analyze my sales CSV. Show revenue by product.
        </p>

        <span className="task-key">↵</span>
      </div>

      <div className="file-chip">
        <FileText size={11} />

        <span>{LIVE_FILE.name}</span>
        <span>{LIVE_FILE.rows} rows · amounts like “$1,200.50”</span>
        <span className="demo-text">SAMPLE FILE</span>
      </div>

      <div className="lifecycle">
        {stages.map((name, index) => (
          <div
            key={name}
            className={[
              'lifecycle-step',
              stage === index && running ? 'active' : '',
              runComplete || index < stage ? 'done' : '',
              reused
                && [1, 4, 5].includes(index)
                && stage >= index
                ? 'skipped'
                : '',
            ].filter(Boolean).join(' ')}
          >
            <div className="step-node">
              {runComplete || index < stage
                ? <Check size={11} />
                : <span>{index + 1}</span>}
            </div>

            <span>{name}</span>
          </div>
        ))}
      </div>

      <div
        className="terminal-output"
        ref={logRef}
        aria-live="polite"
        aria-label="Execution log"
      >
        {!logs.length ? (
          <div className="terminal-idle">
            <div className="terminal-symbol">
              {'>_'}
            </div>

            <div>
              <p>
                Run the sample to see the whole loop
                <span className="cursor">_</span>
              </p>

              <span>
                The first run fails on formatted amounts, repairs the skill
                and saves it. Run it again and the saved skill is reused.
              </span>
            </div>
          </div>
        ) : (
          logs.map((log, index) => (
            <div
              key={index}
              className={`log-line ${log.type || ''}`}
            >
              <span className="log-time">
                {log.time}
              </span>

              <span className="log-tag">
                {log.tag}
              </span>

              <span>{log.message}</span>
            </div>
          ))
        )}

        {runComplete && result && <LiveResult result={result} />}

      </div>

      <div className="console-footer">
        <span>
          <LockKeyhole size={11} />
          {offline ? 'START THE API TO RUN' : 'REAL RUN · SANDBOXED'}
        </span>

        <Button
          className="lime small"
          onClick={onRun}
          disabled={running}
          icon={
            running
              ? AudioLines
              : runComplete
                ? ArrowRight
                : Play
          }
        >
          {running
            ? 'Working on it...'
            : runComplete
              ? 'Run again · reuse the skill'
              : offline
                ? 'Try again'
                : 'Run the sample'}
        </Button>
      </div>
    </section>
  );
}
