import { useEffect, useRef, useState } from 'react';

import { runLive } from '../api/liveRun.js';

// The Live console's sample run: a real task against the API with the bundled sample CSV.
export function useLiveRun({ notify, onFinished }) {
  const [logs, setLogs] = useState([]);
  const [running, setRunning] = useState(false);
  const [runComplete, setRunComplete] = useState(false);
  const [stage, setStage] = useState(-1);
  const [reused, setReused] = useState(false);
  const [offline, setOffline] = useState(false);
  const [liveResult, setLiveResult] = useState(null);

  const alive = useRef(true);
  const inFlight = useRef(false);

  useEffect(() => {
    alive.current = true;

    return () => {
      alive.current = false;
    };
  }, []);

  const runController = useRef(null);

  useEffect(() => () => runController.current?.abort(), []);

  const startRun = async () => {
    if (inFlight.current) {
      return;
    }

    inFlight.current = true;

    const started = Date.now();
    const controller = new AbortController();
    let lines = 0;

    runController.current = controller;

    const push = (line) => {
      if (!alive.current) {
        return;
      }

      lines += 1;
      setStage(line.stage);
      setLogs((previous) => [
        ...previous,
        {
          ...line,
          time: `00:${String(Math.floor((Date.now() - started) / 1000)).padStart(2, '0')}`,
        },
      ]);
    };

    setRunning(true);
    setRunComplete(false);
    setReused(false);
    setLiveResult(null);
    setLogs([]);
    setStage(0);

    try {
      const { execution, repaired } = await runLive({
        onLine: push,
        onWaiting: () => push({
          stage: 0,
          tag: 'WAIT',
          type: '',
          message: 'No worker has picked this up yet. Start one with make worker.',
        }),
        signal: controller.signal,
      });

      if (!alive.current) {
        return;
      }

      const ok = execution?.status === 'succeeded';
      const version = execution?.result?.skill?.version;

      setOffline(false);
      setReused(ok && !repaired);
      setLiveResult(ok ? execution.result : null);
      setRunComplete(ok);
      setStage(ok ? 6 : 4);

      onFinished?.();

      notify(
        !ok
          ? 'The run needs a human. Open Review to retry or reject it.'
          : repaired
            ? `Repaired and saved revenue_by_product v${version}.`
            : `Reused revenue_by_product v${version}. No repair needed.`,
      );
    } catch (error) {
      if (!alive.current || error.name === 'AbortError') {
        return;
      }

      // No API at all: say how to start it instead of pretending.
      if (error.status === 0 && !lines) {
        setOffline(true);
        setStage(-1);
        push({
          stage: -1,
          tag: 'OFFLINE',
          type: 'error',
          message: 'Can’t reach the SkillForge API. Start it with make api and make worker, then run again.',
        });
        return;
      }

      push({ stage: 4, tag: 'FAIL', type: 'error', message: error.message });
      onFinished?.();
    } finally {
      if (runController.current === controller) {
        inFlight.current = false;
        setRunning(false);
      }
    }
  };

  const consoleProps = {
    logs,
    running,
    runComplete,
    stage,
    reused,
    offline,
    result: liveResult,
    onRun: startRun,
  };

  return { consoleProps, running, startRun };
}
