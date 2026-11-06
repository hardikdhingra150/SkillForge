import { describe, expect, it } from "vitest";

import { isTableResult } from "./TaskResult.jsx";

describe("isTableResult", () => {
  it("recognises the built-in spreadsheet results", () => {
    expect(isTableResult({ rows_processed: 5, total_revenue: "10", products: [{ product: "Pen", revenue: "10" }] })).toBe(true);
    expect(isTableResult({ rows_processed: 5, total: "10", groups: [{ group: "EU", total: "10" }] })).toBe(true);
    expect(isTableResult({ rows_processed: 2, headers: ["a"], rows: [["x"]] })).toBe(true);
  });

  it("leaves other skills' outputs to the generic view", () => {
    expect(isTableResult({ groups: [{ group: "Pen", average: "63.75", count: 2 }] })).toBe(false);
    expect(isTableResult({ rows_processed: 5, groups: [{ group: "Pen", average: "63.75" }] })).toBe(false);
    expect(isTableResult({ emails: ["a@b.co"] })).toBe(false);
    expect(isTableResult(null)).toBe(false);
  });
});
