import { describe, expect, it } from "vitest";

import { consoleLine, LIVE_FILE } from "./liveRun.js";

describe("consoleLine", () => {
  it("maps recorded events to console stages and tags", () => {
    expect(consoleLine({ event_type: "step_failed", message: "bad" })).toEqual({ stage: 3, tag: "FAIL", type: "error", message: "bad" });
    expect(consoleLine({ event_type: "skill_promoted", message: "saved" })).toMatchObject({ stage: 5, tag: "SAVE" });
    expect(consoleLine({ event_type: "execution_queued", message: "x" })).toBeUndefined();
  });

  it("ends with REUSE, or DONE after a repair", () => {
    const done = { event_type: "execution_completed", message: "ok" };
    expect(consoleLine(done, false).tag).toBe("REUSE");
    expect(consoleLine(done, true).tag).toBe("DONE");
  });
});

describe("LIVE_FILE", () => {
  it("knows the bundled sample file", () => {
    expect(LIVE_FILE).toEqual({ name: "sales_formatted_amounts.csv", rows: 5 });
  });
});
