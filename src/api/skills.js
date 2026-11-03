import { BASE, request } from "./skillforgeProcess.js";

export function exportUrl(skillId, version) {
  return `${BASE}/skills/${encodeURIComponent(skillId)}/${encodeURIComponent(version)}/export`;
}

export function importSkill(bundle) {
  return request("/skills/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bundle),
  });
}

export function getMcpConfig(signal) {
  return request("/mcp/config", { signal });
}
