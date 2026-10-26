import { useEffect, useRef, useState } from "react";
import {
  getEventsSince,
  getExecution,
  mergeEvents,
  submitTask,
} from "../api/skillforgeProcess.js";

const STORAGE_KEY = "skillforge.process.v1";
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const TERMINAL = new Set(["succeeded", "failed", "cancelled", "expired"]);

function readSaved() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (value?.pending && UUID_PATTERN.test(value.pending.key) &&
        typeof value.pending.requirement === "string") {
      return { executionId: "", pending: value.pending };
    }
    if (UUID_PATTERN.test(value?.executionId || "")) {
      return { executionId: value.executionId, pending: null };
    }
  } catch {
    // A missing or malformed saved view should not stop the page loading.
  }
  return { executionId: "", pending: null };
}

function persist(value) {
  // Save before POST so a page reload can retry with the same key.
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    throw new Error("Browser storage is unavailable. Enable it before submitting a task.");
  }
}

export function useSkillForgeProcess() {
  const [saved, setSaved] = useState(readSaved);
  const [execution, setExecution] = useState(null);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [lastSynced, setLastSynced] = useState(null);
  const [refreshCount, setRefreshCount] = useState(0);
  const submitController = useRef(null);
  const submittingRef = useRef(false);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      submitController.current?.abort();
    };
  }, []);

  useEffect(() => {
    const id = saved.executionId;
    if (!id) return undefined;

    let disposed = false;
    let timer;
    let cursor = 0;
    const controller = new AbortController();
    setLoading(true);

    async function refresh() {
      let delay = 2500;
      let continuePolling = true;
      try {
        const current = await getExecution(id, controller.signal);
        const page = await getEventsSince(id, cursor, controller.signal);
        if (disposed) return;

        cursor = page.nextAfter;
        setExecution(current);
        setEvents((previous) => mergeEvents(previous, page.events));
        setLastSynced(new Date());
        setError("");
        continuePolling = page.hasMore || !TERMINAL.has(current.status);
        if (page.hasMore) delay = 0;
      } catch (failure) {
        if (disposed) return;
        setError(failure.message || "Could not refresh the execution.");
        continuePolling = failure.status !== 404;
        delay = 5000;
      } finally {
        if (!disposed) {
          setLoading(false);
          if (continuePolling) timer = setTimeout(refresh, delay);
        }
      }
    }

    refresh();
    return () => {
      disposed = true;
      clearTimeout(timer);
      controller.abort();
    };
  }, [saved.executionId, refreshCount]);

  async function submit(requirement) {
    if (submittingRef.current) return;
    const normalized = requirement.trim();
    if (normalized.length < 5 || normalized.length > 10000) {
      setError("Enter a requirement between 5 and 10,000 characters.");
      return;
    }
    if (saved.pending && saved.pending.requirement !== normalized) {
      setError("Retry the pending submission or choose New task before changing the requirement.");
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    setError("");
    const controller = new AbortController();
    submitController.current = controller;

    try {
      const pending = saved.pending || {
        key: crypto.randomUUID(),
        requirement: normalized,
      };
      const pendingSaved = { executionId: "", pending };
      persist(pendingSaved);
      setSaved(pendingSaved);
      setExecution(null);
      setEvents([]);
      setLastSynced(null);

      const result = await submitTask(normalized, pending.key, controller.signal);
      if (!mounted.current || controller.signal.aborted) return;
      const completedSaved = { executionId: result.execution_id, pending: null };
      persist(completedSaved);
      setExecution(result);
      setSaved(completedSaved);
    } catch (failure) {
      if (mounted.current && !controller.signal.aborted) {
        setError(failure.message || "Submission failed. Retry with the same requirement.");
      }
    } finally {
      submittingRef.current = false;
      if (mounted.current) setSubmitting(false);
    }
  }

  function openExecution(id) {
    if (submittingRef.current) return;
    const executionId = id.trim();
    if (!UUID_PATTERN.test(executionId)) {
      setError("Enter the task run ID shown in a previous task.");
      return;
    }
    if (saved.pending) {
      setError("Retry the pending submission or choose New task before opening another execution.");
      return;
    }
    try {
      const next = { executionId, pending: null };
      persist(next);
      setExecution(null);
      setEvents([]);
      setLastSynced(null);
      setError("");
      setSaved(next);
      setRefreshCount((count) => count + 1);
    } catch (failure) {
      setError(failure.message);
    }
  }

  function newTask() {
    if (submittingRef.current) return;
    try {
      const next = { executionId: "", pending: null };
      persist(next);
      setSaved(next);
      setExecution(null);
      setEvents([]);
      setLastSynced(null);
      setLoading(false);
      setError("");
    } catch (failure) {
      setError(failure.message);
    }
  }

  return {
    executionId: saved.executionId,
    pending: saved.pending,
    execution,
    events,
    error,
    submitting,
    loading,
    lastSynced,
    submit,
    openExecution,
    newTask,
    refresh: () => setRefreshCount((count) => count + 1),
  };
}
