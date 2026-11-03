// The Live console's real run: submit a task, give it the bundled messy sales CSV, confirm the
// columns, and follow the worker's recorded events. The first run on a fresh registry fails on
// "$1,200.50"-style amounts, repairs the skill and saves a new version; later runs reuse it.
import demoCsv from "../../demo_data/sales_formatted_amounts.csv?raw";
import recordedRun from "../fixtures/recordedRepairRun.json";

import {
  confirmCSVMapping,
  streamExecution,
  submitTask,
  uploadCSVInput,
} from "./skillforgeProcess.js";

export const LIVE_REQUIREMENT = "Show revenue by product";
export const LIVE_FILE = {
  name: "sales_formatted_amounts.csv",
  rows: demoCsv.trim().split("\n").length - 1,
};

const FINISHED = new Set(["succeeded", "failed", "waiting_approval", "cancelled", "expired"]);

// Console stage index (see `stages` in data.js), tag and style for each recorded event type.
const LINES = {
  task_received: [0, "TASK"],
  requirements_checked: [0, "REVIEW"],
  csv_inspected: [0, "INPUT"],
  column_mapping_confirmed: [0, "INPUT"],
  skill_selected: [0, "FIND"],
  plan_created: [1, "PLAN"],
  step_started: [2, "RUN"],
  step_completed: [2, "RUN"],
  validation_started: [3, "TEST"],
  step_failed: [3, "FAIL", "error"],
  validation_failed: [3, "FAIL", "error"],
  repair_started: [4, "PATCH", "repair"],
  repair_candidate: [4, "PATCH", "repair"],
  repair_rejected: [4, "PATCH", "error"],
  repair_applied: [4, "TEST", "success"],
  skill_promoted: [5, "SAVE", "success"],
  validation_passed: [3, "TEST", "success"],
  repair_exhausted: [4, "FAIL", "error"],
  execution_failed: [4, "FAIL", "error"],
};

export function consoleLine(event, repaired) {
  if (event.event_type === "execution_completed") {
    return { stage: 6, tag: repaired ? "DONE" : "REUSE", type: "success", message: event.message };
  }

  const line = LINES[event.event_type];

  return line && { stage: line[0], tag: line[1], type: line[2] || "", message: event.message };
}

// Console lines for the recorded real run, timed as they were recorded.
export function replayLines() {
  let repaired = false;

  return recordedRun.events.flatMap((event) => {
    repaired ||= event.event_type === "skill_promoted";
    const line = consoleLine(event, repaired);
    const seconds = Math.floor(event.at_ms / 1000);

    return line ? [{ ...line, time: `00:${String(seconds).padStart(2, "0")}` }] : [];
  });
}

// Follow the run's stream until `until(execution)` holds; reconnects when the server rotates it.
function follow(executionId, after, onEvent, until, signal) {
  return new Promise((resolve, reject) => {
    let cursor = after;
    let close = () => {};

    const stop = () => {
      close();
      reject(new DOMException("Aborted", "AbortError"));
    };

    signal?.addEventListener("abort", stop, { once: true });

    const finish = (callback) => (value) => {
      signal?.removeEventListener("abort", stop);
      close();
      callback(value);
    };

    const done = finish(resolve);
    const fail = finish(reject);

    const open = () => {
      let latest = null;

      close = streamExecution(executionId, cursor, {
        onEvent(event) {
          cursor = Math.max(cursor, event.sequence);
          onEvent(event);
        },
        onExecution(execution) {
          latest = execution;

          if (until(execution)) {
            done({ execution, cursor });
          }
        },
        onDone() {
          done({ execution: latest, cursor });
        },
        onReconnect: open,
        onError() {
          fail(new Error("Lost the live connection to SkillForge."));
        },
      });
    };

    open();
  });
}

export async function runLive({ onLine, onWaiting, signal }) {
  let repaired = false;

  const onEvent = (event) => {
    repaired ||= event.event_type === "skill_promoted";
    const line = consoleLine(event, repaired);

    if (line) {
      onLine(line);
    }
  };

  const { execution_id: id } = await submitTask(LIVE_REQUIREMENT, crypto.randomUUID(), signal);

  // The worker reviews the requirement; say so if it isn't running.
  const waiting = setTimeout(onWaiting, 12000);
  let reviewed;

  try {
    reviewed = await follow(
      id,
      0,
      onEvent,
      (execution) => execution.status !== "queued" && execution.current_stage !== "requirement_review",
      signal,
    );
  } finally {
    clearTimeout(waiting);
  }

  if (reviewed.execution?.status !== "waiting_input") {
    throw new Error("The requirement review did not accept this task.");
  }

  const file = new File([demoCsv], LIVE_FILE.name, { type: "text/csv" });
  const input = await uploadCSVInput(id, file, signal);

  await confirmCSVMapping(id, {
    file_sha256: input.sha256,
    file_version: input.version,
    product_column: "Product",
    revenue_column: "Sales",
  }, signal);

  const finished = await follow(
    id,
    reviewed.cursor,
    onEvent,
    (execution) => FINISHED.has(execution.status),
    signal,
  );

  return { execution: finished.execution, repaired };
}
