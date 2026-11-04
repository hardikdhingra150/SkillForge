import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../api/skillforgeProcess.js";
import { useSkillForgeProcess } from "./useSkillForgeProcess.js";

vi.mock("../api/skillforgeProcess.js", async (importOriginal) => ({
  ...(await importOriginal()),
  submitTask: vi.fn(),
  getExecution: vi.fn(),
  getEventsSince: vi.fn(),
  streamExecution: vi.fn(),
}));

const RUN = "11c8c542-356a-5a21-953e-cb9464ead17a";
const execution = (status) => ({ execution_id: RUN, status, current_stage: "requirement_review" });

beforeEach(() => {
  localStorage.clear();
  api.submitTask.mockResolvedValue(execution("queued"));
  api.getExecution.mockResolvedValue(execution("succeeded"));
  api.getEventsSince.mockResolvedValue({ events: [{ sequence: 1, message: "saved" }], nextAfter: 1, hasMore: false });
});

afterEach(() => vi.clearAllMocks());

describe("useSkillForgeProcess", () => {
  it("rejects a requirement that is too short", async () => {
    const { result } = renderHook(() => useSkillForgeProcess());
    await act(() => result.current.submit("hi"));
    expect(result.current.error).toMatch(/between 5 and 10,000/);
    expect(api.submitTask).not.toHaveBeenCalled();
  });

  it("submits, remembers the run and loads its events", async () => {
    const { result } = renderHook(() => useSkillForgeProcess());
    await act(() => result.current.submit("  Show revenue by product  "));

    const [requirement, key] = api.submitTask.mock.calls[0];
    expect(requirement).toBe("Show revenue by product");
    expect(key).toMatch(/^[0-9a-f-]{36}$/);
    expect(JSON.parse(localStorage.getItem("skillforge.process.v1"))).toEqual({ executionId: RUN, pending: null });

    await waitFor(() => expect(result.current.execution?.status).toBe("succeeded"));
    expect(result.current.events).toEqual([{ sequence: 1, message: "saved" }]);
    expect(api.streamExecution).not.toHaveBeenCalled();   // finished runs need no live stream
  });

  it("keeps the pending submission key after a failed POST, so a retry is idempotent", async () => {
    api.submitTask.mockRejectedValueOnce(new Error("Cannot reach SkillForge."));
    const { result } = renderHook(() => useSkillForgeProcess());
    await act(() => result.current.submit("Show revenue by product"));
    expect(result.current.error).toBe("Cannot reach SkillForge.");

    await act(() => result.current.submit("Show revenue by product"));
    expect(api.submitTask.mock.calls[1][1]).toBe(api.submitTask.mock.calls[0][1]);
  });

  it("validates run IDs before opening them", () => {
    const { result } = renderHook(() => useSkillForgeProcess());
    let opened;
    act(() => { opened = result.current.openExecution("not-a-run"); });
    expect(opened).toBe(false);
    expect(result.current.error).toMatch(/task run ID/);
  });

  it("New task clears the current run", async () => {
    localStorage.setItem("skillforge.process.v1", JSON.stringify({ executionId: RUN, pending: null }));
    const { result } = renderHook(() => useSkillForgeProcess());
    await waitFor(() => expect(result.current.execution).not.toBeNull());
    act(() => result.current.newTask());
    expect(result.current.executionId).toBe("");
    expect(result.current.execution).toBeNull();
  });
});
