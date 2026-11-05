export const BASE = (
  import.meta.env?.VITE_API_BASE_URL
  || "http://127.0.0.1:8000/api/v1"
).replace(/\/+$/, "");

const TOKEN_KEY = "skillforge.apiToken";

// The API access token (API_TOKEN on the server), kept in this browser only.
export function getApiToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

export function setApiToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // Storage blocked: the token simply is not remembered.
  }
}

// EventSource cannot send headers, so live streams carry the token in the query string.
export function streamUrl(path) {
  const token = getApiToken();

  if (!token) {
    return `${BASE}${path}`;
  }

  return `${BASE}${path}${path.includes("?") ? "&" : "?"}access_token=${encodeURIComponent(token)}`;
}

export class ProcessApiError extends Error {
  constructor(message, status = 0) {
    super(message);

    this.name = "ProcessApiError";
    this.status = status;
  }
}

export async function request(path, options = {}) {
  const { signal, ...rest } = options;

  const controller = new AbortController();
  let timedOut = false;

  const abort = () => controller.abort();

  if (signal?.aborted) {
    abort();
  }

  signal?.addEventListener(
    "abort",
    abort,
    { once: true },
  );

  const timeout = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, 15000);

  try {
    const response = await fetch(
      `${BASE}${path}`,
      {
        ...rest,
        signal: controller.signal,
        headers: {
          Accept: "application/json",
          ...(getApiToken() ? { Authorization: `Bearer ${getApiToken()}` } : {}),
          ...rest.headers,
        },
      },
    );

    const body = await response
      .json()
      .catch(() => null);

    if (!response.ok) {
      const detail = body?.detail;

      const message = Array.isArray(detail)
        ? detail.map((item) => item.msg).join("; ")
        : typeof detail === "string"
          ? detail
          : detail?.message;

      if (response.status === 401) {
        throw new ProcessApiError(
          "This SkillForge API needs an access token. Add it in Workspace settings (the gear button, top right).",
          401,
        );
      }

      throw new ProcessApiError(
        message
          || `Request failed (HTTP ${response.status}).`,
        response.status,
      );
    }

    if (body === null) {
      throw new ProcessApiError(
        "The API returned an invalid JSON response.",
      );
    }

    return body;
  } catch (error) {
    if (signal?.aborted) {
      throw error;
    }

    if (timedOut) {
      throw new ProcessApiError(
        "The API request timed out. You can retry.",
      );
    }

    if (error instanceof ProcessApiError) {
      throw error;
    }

    throw new ProcessApiError(
      "Cannot reach SkillForge. Check FastAPI and the frontend CORS origin.",
    );
  } finally {
    clearTimeout(timeout);

    signal?.removeEventListener(
      "abort",
      abort,
    );
  }
}

// Submit a requirement using its existing submission key.
export function submitTask(
  requirement,
  key,
  signal,
) {
  return request("/tasks", {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": key,
    },
    body: JSON.stringify({
      requirement,
    }),
  });
}

// Load one saved execution.
export function getExecution(
  executionId,
  signal,
) {
  return request(
    `/executions/${encodeURIComponent(executionId)}`,
    { signal },
  );
}

// Load recorded events, continuing through bounded pages.
export async function getEventsSince(
  executionId,
  after = 0,
  signal,
) {
  const events = [];

  let cursor = after;
  let hasMore = false;

  for (let page = 0; page < 20; page += 1) {
    const params = new URLSearchParams({
      after: String(cursor),
      limit: "100",
    });

    const result = await request(
      `/executions/${encodeURIComponent(executionId)}/events?${params}`,
      { signal },
    );

    if (
      !Array.isArray(result.events)
      || !Number.isSafeInteger(result.next_after)
      || result.next_after < cursor
      || (
        result.has_more
        && result.next_after <= cursor
      )
    ) {
      throw new ProcessApiError(
        "The API returned an invalid event cursor.",
      );
    }

    events.push(...result.events);

    cursor = result.next_after;
    hasMore = Boolean(result.has_more);

    if (!hasMore) {
      break;
    }
  }

  return {
    events,
    nextAfter: cursor,
    hasMore,
  };
}

// Follow one run live over server-sent events. Returns a close function.
export function streamExecution(
  executionId,
  after,
  { onExecution, onEvent, onDone, onReconnect, onError },
) {
  const source = new EventSource(
    streamUrl(`/executions/${encodeURIComponent(executionId)}/stream?after=${after}`),
  );

  source.addEventListener("execution", (message) => onExecution(JSON.parse(message.data)));
  source.addEventListener("event", (message) => onEvent(JSON.parse(message.data)));
  source.addEventListener("done", () => { source.close(); onDone?.(); });
  // The server ends each stream after 30 s; carry on from the last event.
  source.addEventListener("reconnect", () => { source.close(); onReconnect?.(); });
  source.onerror = () => { source.close(); onError?.(); };

  return () => source.close();
}

// Merge events without repeating the same sequence.
export function mergeEvents(previous, incoming) {
  const bySequence = new Map(
    previous.map((event) => [
      event.sequence,
      event,
    ]),
  );

  for (const event of incoming) {
    bySequence.set(event.sequence, event);
  }

  return [...bySequence.values()].sort(
    (a, b) => a.sequence - b.sequence,
  );
}

// Load uploaded CSV metadata and preview.
export function getCSVInput(
  executionId,
  signal,
) {
  return request(
    `/executions/${encodeURIComponent(executionId)}/input`,
    { signal },
  );
}

// Upload a CSV. The browser sets the multipart Content-Type.
export function uploadCSVInput(
  executionId,
  file,
  signal,
) {
  const form = new FormData();
  form.append("file", file);

  return request(
    `/executions/${encodeURIComponent(executionId)}/input`,
    {
      method: "POST",
      body: form,
      signal,
    },
  );
}

// Confirm the selected product and revenue columns.
export function confirmCSVMapping(
  executionId,
  mapping,
  signal,
) {
  return request(
    `/executions/${encodeURIComponent(executionId)}/input/confirm`,
    {
      method: "POST",
      signal,
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(mapping),
    },
  );
}

// Load saved skill versions from the registry.
export function getSkillRegistry(
  options = {},
  signal,
) {
  const params = new URLSearchParams({
    limit: String(options.limit ?? 24),
  });

  if (options.status) {
    params.set("status", options.status);
  }

  if (options.query) {
    params.set("q", options.query);
  }

  if (options.afterSkillId != null) {
    params.set(
      "after_skill_id",
      options.afterSkillId,
    );
  }

  if (options.afterVersion != null) {
    params.set(
      "after_version",
      options.afterVersion,
    );
  }

  return request(
    `/skills?${params}`,
    { signal },
  );
}

// Load previous task runs for Activity and the task picker.
export function getSavedExecutions(
  options = {},
  signal,
) {
  const params = new URLSearchParams({
    limit: String(options.limit ?? 24),
  });

  if (options.status) {
    params.set("status", options.status);
  }

  if (options.query) {
    params.set("q", options.query);
  }

  if (options.beforeCreatedAt != null) {
    params.set(
      "before_created_at",
      options.beforeCreatedAt,
    );
  }

  if (options.beforeExecutionId != null) {
    params.set(
      "before_execution_id",
      options.beforeExecutionId,
    );
  }

  return request(
    `/executions?${params}`,
    { signal },
  );
}
export function submitClarification(executionId, answer) {
  return request(`/executions/${encodeURIComponent(executionId)}/clarify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });
}

// Real workspace numbers for the Workbench metric cards.
export function getMetricsSummary(signal) {
  return request("/metrics/summary", { signal });
}
