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

// The optional reason is recorded in the audit trail.
export function retireVersion(skillId, version, reason) {
  return post(`/skills/${encodeURIComponent(skillId)}/${encodeURIComponent(version)}/retire`, reason ? { reason } : {});
}

export function restoreVersion(skillId, version, reason) {
  return post(`/skills/${encodeURIComponent(skillId)}/${encodeURIComponent(version)}/restore`, reason ? { reason } : {});
}

export function getAuditTrail(signal, limit = 30) {
  return request(`/audit?limit=${limit}`, { signal });
}
