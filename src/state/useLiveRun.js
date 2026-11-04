import { useEffect, useRef, useState } from 'react';

import { replayLines, runLive } from '../api/liveRun.js';
import recordedRun from '../fixtures/recordedRepairRun.json';

const sleep = (ms) => (
  new Promise((resolve) => setTimeout(resolve, ms))
);

// The Live console's run: real against the API, or a recorded real run when the API is offline.
export function useLiveRun({ notify, onRepaired }) {
  const [logs, setLogs] = useState([]);
  const [running, setRunning] = useState(false);
  const [runComplete, setRunComplete] = useState(false);
  const [stage, setStage] = useState(-1);
  const [reused, setReused] = useState(false);
  // The console runs for real against the API; the recorded replay is only a fallback.
  const [consoleLive, setConsoleLive] = useState(true);
  const [liveResult, setLiveResult] = useState(null);

  const alive = useRef(true);
  const inFlight = useRef(false);

  useEffect(() => {
    alive.current = true;

    return () => {
      alive.current = false;
    };
  }, []);

  // Offline: replay a recorded real run (src/fixtures/recordedRepairRun.json) at a readable pace.
  const playDemo = async () => {
    if (inFlight.current) {
      return;
    }

    inFlight.current = true;
    setRunning(true);
    setRunComplete(false);
    setReused(false);
    setLiveResult(null);
    setLogs([]);
    setStage(0);

    for (const line of replayLines()) {
      if (!alive.current) {
        return;
      }

      setStage(line.stage);
      setLogs((previous) => [...previous, line]);
      await sleep(line.type === 'error' ? 1400 : 800);
    }

    if (!alive.current) {
      return;
    }

    setLiveResult(recordedRun.result);
    setRunComplete(true);
    setStage(6);
    setRunning(false);
    inFlight.current = false;
    notify('That was a recorded real run. Start the API and worker to run it live.');
  };

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

      setConsoleLive(true);
      setReused(ok && !repaired);
      setLiveResult(ok ? execution.result : null);
      setRunComplete(ok);
      setStage(ok ? 6 : 4);

      if (ok && repaired) {
        onRepaired();
      }

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

      // No API at all: fall back to the scripted demo.
      if (error.status === 0 && !lines) {
        setConsoleLive(false);
        inFlight.current = false;
        setRunning(false);
        await playDemo();
        return;
      }

      push({ stage: 4, tag: 'FAIL', type: 'error', message: error.message });
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
    live: consoleLive,
    result: liveResult,
    onRun: startRun,
  };

  return { consoleProps, running, startRun };
}
