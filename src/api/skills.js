import { request } from "./skillforgeProcess.js";

// Fetch the bundle (so the access token is sent) and save it as a file.
export async function downloadBundle(skillId, version) {
  const bundle = await request(`/skills/${encodeURIComponent(skillId)}/${encodeURIComponent(version)}/export`);
  const url = URL.createObjectURL(new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");

  link.href = url;
  link.download = `${skillId}-v${version}.skillforge.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
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
