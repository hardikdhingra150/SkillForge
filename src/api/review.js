import { request } from "./skillforgeProcess.js";

const post = (path, body = {}) => request(path, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export function getReviewQueue(signal) {
  return request("/review", { signal });
}

export function retryRun(executionId, extraBudget = 2) {
  return post(`/executions/${encodeURIComponent(executionId)}/review/retry`, { extra_budget: extraBudget });
}

export function rejectRun(executionId, reason) {
  return post(`/executions/${encodeURIComponent(executionId)}/review/reject`, reason ? { reason } : {});
}

export function retireVersion(skillId, version) {
  return post(`/skills/${encodeURIComponent(skillId)}/${encodeURIComponent(version)}/retire`);
}

export function restoreVersion(skillId, version) {
  return post(`/skills/${encodeURIComponent(skillId)}/${encodeURIComponent(version)}/restore`);
}

export function getAuditTrail(signal, limit = 30) {
  return request(`/audit?limit=${limit}`, { signal });
}
