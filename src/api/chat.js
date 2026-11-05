import { request, streamUrl } from "./skillforgeProcess.js";

const json = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export function getProviders({ refresh = false } = {}, signal) {
  return request(`/providers${refresh ? "?refresh=true" : ""}`, { signal });
}

export function listConversations(signal) {
  return request("/conversations", { signal });
}

export function createConversation(provider, model) {
  return request("/conversations", json({ provider, model: model || null }));
}

export function getConversation(id, signal) {
  return request(`/conversations/${encodeURIComponent(id)}`, { signal });
}

export function deleteConversation(id) {
  return request(`/conversations/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function sendMessage(id, content, provider, model, attachmentIds = []) {
  return request(`/conversations/${encodeURIComponent(id)}/messages`,
    json({ content, provider, model: model || null, attachment_ids: attachmentIds }));
}

export function uploadAttachment(id, file) {
  const form = new FormData();
  form.append("file", file);
  return request(`/conversations/${encodeURIComponent(id)}/attachments`, { method: "POST", body: form });
}

/** Live updates for a conversation (server-sent events). Returns a close function. */
export function streamConversation(id, { onUpdate, onDone, onError }) {
  const source = new EventSource(streamUrl(`/conversations/${encodeURIComponent(id)}/stream`));
  source.addEventListener("update", (event) => onUpdate(JSON.parse(event.data)));
  source.addEventListener("done", () => { source.close(); onDone?.(); });
  source.onerror = () => { source.close(); onError?.(); };
  return () => source.close();
}

export function getScoreboard(signal) {
  return request("/scoreboard", { signal });
}
