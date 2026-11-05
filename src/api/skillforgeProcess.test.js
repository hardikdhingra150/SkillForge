import { afterEach, describe, expect, it, vi } from "vitest";

import { getEventsSince, mergeEvents, ProcessApiError, request, setApiToken, streamUrl } from "./skillforgeProcess.js";

function respond(status, body) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => (body === undefined ? Promise.reject(new SyntaxError("no body")) : Promise.resolve(body)),
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  setApiToken("");
});

describe("mergeEvents", () => {
  it("keeps one event per sequence, sorted, with the newest copy winning", () => {
    const merged = mergeEvents(
      [{ sequence: 2, message: "old" }, { sequence: 1, message: "a" }],
      [{ sequence: 3, message: "c" }, { sequence: 2, message: "new" }],
    );
    expect(merged.map((event) => [event.sequence, event.message])).toEqual([[1, "a"], [2, "new"], [3, "c"]]);
  });
});

describe("request error handling", () => {
  it("returns the JSON body on success", async () => {
    vi.stubGlobal("fetch", respond(200, { ok: true }));
    await expect(request("/x")).resolves.toEqual({ ok: true });
  });

  it("uses a string detail as the message and keeps the status", async () => {
    vi.stubGlobal("fetch", respond(409, { detail: "This run is queued." }));
    await expect(request("/x")).rejects.toMatchObject({ message: "This run is queued.", status: 409 });
  });

  it("joins FastAPI validation errors", async () => {
    vi.stubGlobal("fetch", respond(422, { detail: [{ msg: "too short" }, { msg: "bad id" }] }));
    await expect(request("/x")).rejects.toThrow("too short; bad id");
  });

  it("falls back to the HTTP status when there is no detail", async () => {
    vi.stubGlobal("fetch", respond(500, undefined));
    await expect(request("/x")).rejects.toThrow("Request failed (HTTP 500).");
  });

  it("rejects a successful response without JSON", async () => {
    vi.stubGlobal("fetch", respond(200, undefined));
    await expect(request("/x")).rejects.toThrow("invalid JSON");
  });

  it("reports an unreachable API with status 0", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const error = await request("/x").catch((caught) => caught);
    expect(error).toBeInstanceOf(ProcessApiError);
    expect(error.status).toBe(0);
    expect(error.message).toMatch(/Cannot reach SkillForge/);
  });
});

describe("getEventsSince", () => {
  it("follows pages until has_more is false", async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ events: [{ sequence: 1 }], next_after: 1, has_more: true }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ events: [{ sequence: 2 }], next_after: 2, has_more: false }) });
    vi.stubGlobal("fetch", fetch);
    await expect(getEventsSince("run", 0)).resolves.toEqual({ events: [{ sequence: 1 }, { sequence: 2 }], nextAfter: 2, hasMore: false });
    expect(fetch.mock.calls[1][0]).toContain("after=1");
  });

  it("rejects a cursor that moves backwards", async () => {
    vi.stubGlobal("fetch", respond(200, { events: [], next_after: 3, has_more: false }));
    await expect(getEventsSince("run", 5)).rejects.toThrow("invalid event cursor");
  });
});

describe("API access token", () => {
  it("sends no Authorization header without a token", async () => {
    const fetch = respond(200, {});
    vi.stubGlobal("fetch", fetch);
    await request("/x");
    expect(fetch.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  it("sends the saved token as a bearer token", async () => {
    setApiToken("secret-token");
    const fetch = respond(200, {});
    vi.stubGlobal("fetch", fetch);
    await request("/x");
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer secret-token");
  });

  it("explains a 401 and where to add the token", async () => {
    vi.stubGlobal("fetch", respond(401, { detail: { code: "UNAUTHORIZED" } }));
    await expect(request("/x")).rejects.toMatchObject({ status: 401, message: expect.stringMatching(/Workspace settings/) });
  });

  it("puts the token in stream URLs, which cannot carry headers", () => {
    expect(streamUrl("/conversations/c/stream")).not.toContain("access_token");
    setApiToken("a b");
    expect(streamUrl("/conversations/c/stream")).toMatch(/\/conversations\/c\/stream\?access_token=a%20b$/);
    expect(streamUrl("/executions/e/stream?after=3")).toMatch(/after=3&access_token=a%20b$/);
  });
});
