import { request } from "./skillforgeProcess.js";

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

export function sendMessage(id, content, provider, model) {
  return request(`/conversations/${encodeURIComponent(id)}/messages`, json({ content, provider, model: model || null }));
}
