import { describe, expect, it } from "vitest";

import { consoleLine, LIVE_FILE, replayLines } from "./liveRun.js";

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

describe("replayLines", () => {
  it("replays the recorded repair run in order with timestamps", () => {
    const lines = replayLines();
    const tags = lines.map((line) => line.tag);
    expect(tags.indexOf("FAIL")).toBeLessThan(tags.indexOf("PATCH"));
    expect(tags.indexOf("PATCH")).toBeLessThan(tags.indexOf("SAVE"));
    expect(tags.at(-1)).toBe("DONE");
    expect(lines.every((line) => /^00:\d\d$/.test(line.time))).toBe(true);
  });

  it("knows the bundled demo file", () => {
    expect(LIVE_FILE).toEqual({ name: "sales_formatted_amounts.csv", rows: 5 });
  });
});
