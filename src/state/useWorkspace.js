import { useCallback, useEffect, useRef, useState } from 'react';

import {
  getMetricsSummary,
  getSavedExecutions,
  getSkillRegistry,
  request,
} from '../api/skillforgeProcess.js';

const REFRESH_MS = 20000;

// What the workspace really looks like right now: API status, numbers, latest runs and skills.
// status: 'checking' | 'online' | 'offline' (no API) | 'locked' (needs an access token) | 'degraded' (no database)
export function useWorkspace() {
  const [state, setState] = useState({
    status: 'checking',
    metrics: null,
    runs: [],
    skills: [],
    checkedAt: null,
  });

  const controller = useRef(null);

  const refresh = useCallback(async () => {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    const { signal } = current;

    try {
      await request('/health/ready', { signal });
    } catch (error) {
      if (error.name === 'AbortError') {
        return;
      }

      setState((previous) => ({
        ...previous,
        status: error.status === 0 ? 'offline' : 'degraded',
        checkedAt: new Date(),
      }));
      return;
    }

    try {
      const [metrics, runs, skills] = await Promise.all([
        getMetricsSummary(signal),
        getSavedExecutions({ limit: 5 }, signal),
        getSkillRegistry({ limit: 6, status: 'validated' }, signal),
      ]);

      setState({
        status: 'online',
        metrics,
        runs: runs.items || [],
        skills: skills.items || [],
        checkedAt: new Date(),
      });
    } catch (error) {
      if (error.name === 'AbortError') {
        return;
      }

      setState((previous) => ({
        ...previous,
        status: error.status === 401 ? 'locked' : error.status === 0 ? 'offline' : 'degraded',
        checkedAt: new Date(),
      }));
    }
  }, []);

  useEffect(() => {
    refresh();

    const timer = setInterval(refresh, REFRESH_MS);
    const onFocus = () => refresh();

    window.addEventListener('focus', onFocus);

    return () => {
      clearInterval(timer);
      window.removeEventListener('focus', onFocus);
      controller.current?.abort();
    };
  }, [refresh]);

  return { ...state, refresh };
}

export const STATUS_LABEL = {
  checking: 'CHECKING THE API',
  online: 'CONNECTED',
  offline: 'API OFFLINE',
  locked: 'ACCESS TOKEN NEEDED',
  degraded: 'DATABASE UNAVAILABLE',
};
