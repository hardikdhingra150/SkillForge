export function getSavedExecutions(options = {}, signal) {
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