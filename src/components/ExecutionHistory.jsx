import {
    useCallback,
    useEffect,
    useId,
    useRef,
    useState,
  } from "react";
  
  import {
    getSavedExecutions,
  } from "../api/skillforgeProcess.js";
  
  import "./execution-history.css";
  
  
  const STATUSES = [
    "queued",
    "running",
    "waiting_input",
    "waiting_approval",
    "cancel_requested",
    "succeeded",
    "failed",
    "cancelled",
    "expired",
  ];
  
  
  export default function ExecutionHistory({
    compact = false,
    onOpen,
    disabled = false,
  }) {
    const uid = useId();
  
    const Heading = compact ? "h3" : "h1";
  
    const [items, setItems] = useState([]);
    const [status, setStatus] = useState("");
    const [draft, setDraft] = useState("");
    const [query, setQuery] = useState("");
    const [cursor, setCursor] = useState(null);
    const [hasMore, setHasMore] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [refresh, setRefresh] = useState(0);
  
    const activeRequest = useRef(null);
  
    const applyPage = useCallback(
      (page, append) => {
        setItems((previous) => {
          if (!append) {
            return page.items;
          }
  
          const byId = new Map(
            previous.map((item) => [
              item.execution_id,
              item,
            ]),
          );
  
          for (const item of page.items) {
            byId.set(
              item.execution_id,
              item,
            );
          }
  
          return [...byId.values()];
        });
  
        setHasMore(page.has_more);
  
        setCursor(
          page.has_more
            ? {
                beforeCreatedAt:
                  page.next_before_created_at,
                beforeExecutionId:
                  page.next_before_execution_id,
              }
            : null,
        );
      },
      [],
    );
  
    useEffect(() => {
      const controller =
        new AbortController();
  
      activeRequest.current = controller;
  
      setItems([]);
      setCursor(null);
      setHasMore(false);
      setError("");
      setLoading(true);
  
      getSavedExecutions(
        {
          status,
          query,
          limit: compact ? 6 : 24,
        },
        controller.signal,
      )
        .then((page) => {
          if (!controller.signal.aborted) {
            applyPage(page, false);
          }
        })
        .catch((failure) => {
          if (!controller.signal.aborted) {
            setError(failure.message);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        });
  
      return () => {
        activeRequest.current?.abort();
      };
    }, [
      status,
      query,
      compact,
      refresh,
      applyPage,
    ]);
  
    async function loadMore() {
      if (loading || !cursor) return;
  
      const controller =
        new AbortController();
  
      activeRequest.current = controller;
  
      setLoading(true);
      setError("");
  
      try {
        const page =
          await getSavedExecutions(
            {
              status,
              query,
              limit: compact ? 6 : 24,
              ...cursor,
            },
            controller.signal,
          );
  
        if (!controller.signal.aborted) {
          applyPage(page, true);
        }
      } catch (failure) {
        if (!controller.signal.aborted) {
          setError(failure.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }
  
    return (
      <section
        className={
          `sf-history ${
            compact
              ? "sf-history--compact"
              : ""
          }`
        }
        aria-labelledby={`${uid}-title`}
      >
        <header className="sf-history__header">
          <div>
            <Heading id={`${uid}-title`}>
              {compact
                ? "Open a previous task"
                : "Your activity"}
            </Heading>
  
            <p>
              Browse saved task runs and open
              their recorded progress and
              results.
            </p>
          </div>
  
          <button
            type="button"
            onClick={() =>
              setRefresh(
                (value) => value + 1,
              )
            }
            disabled={loading}
          >
            Refresh tasks
          </button>
        </header>
  
        <form
          className="sf-history__filters"
          onSubmit={(event) => {
            event.preventDefault();
            setQuery(draft.trim());
          }}
        >
          <label htmlFor={`${uid}-query`}>
            Search tasks
  
            <input
              id={`${uid}-query`}
              maxLength={100}
              value={draft}
              placeholder={
                "Search previous requirements"
              }
              onChange={(event) =>
                setDraft(
                  event.target.value,
                )
              }
            />
          </label>
  
          <button type="submit">
            Search
          </button>
  
          <label htmlFor={`${uid}-status`}>
            Status
  
            <select
              id={`${uid}-status`}
              value={status}
              onChange={(event) =>
                setStatus(
                  event.target.value,
                )
              }
            >
              <option value="">
                All statuses
              </option>
  
              {STATUSES.map((value) => (
                <option
                  value={value}
                  key={value}
                >
                  {value.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
        </form>
  
        <p
          className="sf-history__muted"
          role="status"
        >
          {loading
            ? "Loading tasks…"
            : `${items.length} saved run${
                items.length === 1 ? "" : "s"
              } loaded`}
        </p>
  
        {disabled && (
          <p className="sf-history__muted">
            Finish or clear the pending
            submission before opening
            another task.
          </p>
        )}
  
        {error && (
          <div
            className="sf-history__error"
            role="alert"
          >
            <p>{error}</p>
  
            <button
              type="button"
              onClick={() =>
                setRefresh(
                  (value) => value + 1,
                )
              }
            >
              Retry
            </button>
          </div>
        )}
  
        {!loading &&
          !error &&
          items.length === 0 && (
            <p className="sf-history__empty">
              {query || status
                ? "No tasks match these filters."
                : "No saved tasks yet. Submit a requirement to start."}
            </p>
          )}
  
        <ol className="sf-history__list">
          {items.map((item) => (
            <li
              className="sf-history__item"
              key={item.execution_id}
            >
              <div>
                <p className="sf-history__requirement">
                  {
                    item.requirement_preview
                  }
                </p>
  
                <p className="sf-history__muted">
                  <time
                    dateTime={item.created_at}
                  >
                    {new Date(
                      item.created_at,
                    ).toLocaleString()}
                  </time>
  
                  {" · Stage: "}
  
                  {item.current_stage.replaceAll(
                    "_",
                    " ",
                  )}
                </p>
  
                <span
                  className="sf-history__badge"
                  data-status={item.status}
                >
                  {item.status.replaceAll(
                    "_",
                    " ",
                  )}
                </span>
              </div>
  
              <button
                type="button"
                disabled={
                  disabled || !onOpen
                }
                onClick={() =>
                  onOpen(
                    item.execution_id,
                  )
                }
              >
                Open task
              </button>
            </li>
          ))}
        </ol>
  
        {hasMore && (
          <button
            type="button"
            onClick={loadMore}
            disabled={loading}
          >
            {loading
              ? "Loading…"
              : "Load more tasks"}
          </button>
        )}
      </section>
    );
  }