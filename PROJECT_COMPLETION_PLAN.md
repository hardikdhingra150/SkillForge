# SkillForge: step-by-step plan to finish the project

_Written 1 November 2026. Based on the code in `main` plus the uncommitted cleanup._

**Goal:** make everything the landing page and promo video promise actually work end to end (**discover → create → execute → evaluate → repair → version → reuse**), then ship it publicly.

Each phase lists **steps**, the **files** involved, and a **"done when"** check. Do the phases in order: each one builds on the last.

---

## Where you are now

| Layer | Done | Missing |
|---|---|---|
| Frontend | Themed landing page, workspace, Process view, Skill library, Activity, scroll and pop animations, dark and light modes | The Live console runs a **scripted** demo; the metrics are sample data; `App.jsx` is about 2,600 lines; no tests |
| API | `POST /tasks`, `GET /executions`, `GET /executions/{id}`, `GET /executions/{id}/events`, CSV `input` / `input/confirm`, `GET /skills`, health checks | Metrics, live updates over SSE, repair approval, skill source and diffs |
| Worker | Reviews requirements; runs the confirmed CSV with **one** built-in skill and validates the result | **Create** and **repair** stages, promoting new versions |
| Data | `Task`, `Execution`, `ExecutionEvent`, `ExecutionCSVInput`, `SkillVersion` (hash and validation evidence) | Skill source code, contract, parent version, repair history |
| Quality | 34 backend unit tests | CI, frontend tests, linting |
| Shipping | Runs locally | Hosting, auth, a public demo |

**Phases 0 and 1 are done.** The next action is **Phase 2**: the skill platform.

---

## Phase 0: commit the cleanup (about 10 minutes)

1. Review the uncommitted diff: `.gitignore`, the untracked caches and env files, the `*.example` files, `README.md`, `CHANGES_AND_ROADMAP.md`.
2. Commit and push:

   ```sh
   git add -A && git commit -m "Clean up repo: ignore caches and env files, add env examples, rewrite README" && git push
   ```

3. Optional: shrink the repo history by removing the old MP4 and caches with `git filter-repo`. This rewrites history, so only do it if nobody else has cloned the repo.

**Done when** `git ls-files | grep -E "pycache|\.env$|\.mp4"` prints nothing.

---

## Phase 1: developer foundations (1–2 days) ✅ Done

_Shipped: a `Makefile`, `ruff` (in `backend/pyproject.toml` and `requirements-dev.txt`), ESLint 9 (`eslint.config.js`, `npm run lint`) and GitHub Actions CI (`.github/workflows/ci.yml`). Prettier was left out on purpose: reformatting every file would bury real changes in a huge diff. Add it when you split `App.jsx` in Phase 7._


So that every later change is safe to make.

1. **A single dev command.** Add a `Makefile` (or npm scripts) with:
   - `make db`: `docker compose up -d postgres`
   - `make migrate`: `alembic upgrade head`
   - `make seed`: `python -m app.register_builtin_skills`
   - `make api`, `make worker`, `make web`
   - `make test`: backend tests plus the frontend build
2. **Linting.**
   - Backend: add `ruff`, with a `pyproject.toml` config.
   - Frontend: add ESLint (with `eslint-plugin-react-hooks`) and Prettier.
3. **CI.** Add `.github/workflows/ci.yml`:
   - **backend job:** set up Python, `pip install -r backend/requirements.txt ruff`, `ruff check backend`, then `python -m unittest discover backend/tests`.
   - **frontend job:** `npm ci`, `npm run lint`, `npm run build`.
   - **integration job (later):** a `postgres:18` service, `alembic upgrade head`, then the API tests.
4. **Pin the dev tools.** Create `backend/requirements-dev.txt` with `ruff` and `pytest` (optional; unittest already works).

**Done when** a push to GitHub runs CI and it's green.

---

## Phase 2: a skill platform that can hold more than one skill (3–4 days)

Today `SkillVersion` only points at Python code that lives in the repo (`builtin_sales.py`). Generated and repaired skills need their **code, contract and history stored in the database**.

1. **Define a skill contract schema** in `backend/app/schemas/skill_contract.py`, using Pydantic:

   ```text
   SkillContract
     capability: str                 # e.g. "revenue_by_product"
     inputs:  {name, type, required, description}[]   # e.g. sales_csv, product_column, revenue_column
     outputs: {name, type}[]         # e.g. products[], total_revenue
     tools:   list[str]              # allowlist, e.g. ["read_csv", "group_sum"]
     checks:  list[str]              # validation rules to run
   ```

2. **Extend `SkillVersion`** with a new Alembic migration in `backend/migrations/versions/`:
   - `source_code TEXT`: the skill's Python source.
   - `contract_json JSONB`.
   - `parent_version VARCHAR(32) NULL`: the version this one was repaired or derived from.
   - `origin VARCHAR(20)`: one of `builtin`, `generated` or `repaired`.
   - `change_json JSONB NULL`: the repair diff, the reason, and the failing evidence.

   Backfill the built-in sales skill with its source and contract in `register_builtin_skills.py`.

3. **A tool manager** in `backend/app/services/tools.py`: a registry of approved, pure functions such as `read_csv`, `group_sum`, `to_decimal` and `parse_date`. Skills receive **only** a `tools` object; they never import `os`, `subprocess`, sockets and so on.

4. **A sandbox runner** in `backend/app/services/sandbox.py`:
   - **Static check:** parse the skill source with `ast` and reject imports, `exec`/`eval`, attribute access to dunders, and file or network names.
   - **Run** the skill in a **subprocess** with a timeout (for example 10 seconds), memory and CPU limits (`resource.setrlimit`), no network, and only the tools object plus JSON input passed in.
   - Return `{ok, output, error, duration_ms}`.
   - Later hardening: run it in a container (Phase 8).

5. **A generic executor.** Change `execution_queue.execute_next` to:
   - load the selected `SkillVersion` (source and contract),
   - run it through the sandbox,
   - then run the contract checks,

   instead of calling `run_sales` directly. Keep `builtin_sales` as the first stored skill.

6. **Tests:** contract validation, sandbox rejection cases (`import os`, `open()`, an infinite loop hitting the timeout), and the executor running the stored sales skill.

**Done when** the sales skill runs from **database-stored source** through the sandbox, and all tests pass.

---

## Phase 3: the real repair loop, the story from the video (4–5 days)

Make "revenue vs Sales → repaired → v1.1 → reused" real.

1. **Classify failures** in `backend/app/services/failures.py`. Turn exceptions and validation errors into typed failures:
   - `MISSING_COLUMN(expected, available_headers)`
   - `BAD_NUMBER_FORMAT(column, sample)`, for example `$1,200` or `1.200,50`
   - `EMPTY_ROWS`
   - `CHECK_FAILED(check, details)`
2. **Repair strategies** in `backend/app/services/repair.py`. Make them deterministic first; the LLM comes in Phase 4.
   - **Column alias:** match the expected name against the headers using a synonym table (`revenue ↔ sales, amount, total`) plus fuzzy similarity. Patch the skill's column map.
   - **Number normaliser:** strip currency symbols and thousands separators by switching the skill to the `to_decimal` tool.
   - **Row filter:** skip blank rows.
   - Each strategy returns `(new_source, change_summary, diff)`.
3. **Add the repair stage to the worker** (`execution_queue.py`). On failure:
   1. Emit `repair_started`.
   2. Try the matching strategies in turn, up to a **repair budget** (setting `REPAIR_BUDGET=2`).
   3. After each attempt, rerun the sandbox and **all** contract checks.
   4. On success, emit `repair_applied` and `validation_passed`, then **promote** a new `SkillVersion` (`1.0.0 → 1.1.0`, `origin=repaired`, `parent_version`, `change_json` holding the diff, reason and test evidence) and finish the run as `succeeded`.
   5. If the budget runs out, emit `repair_exhausted` and set the status to `needs_review`. This is a new status, so add it to the model and API.
4. **Reuse.** In discovery, pick the **newest validated version** for the capability, so the next run uses v1.1 and needs no repair.
5. **A demo fixture** at `demo_data/sales_renamed_column.csv`: the same data with the revenue column named differently from the mapping saved in v1.0. Make sure the confirm step lets this flow happen. For example, when a task reuses the mapping saved by a previous skill version, the worker should detect that the column is missing instead of asking the user again.
6. **Tests:** each strategy, a budget cut-off, the promotion record, and a reuse run selecting v1.1.

**Done when** two real runs in a row show (a) fail → repair → v1.1 saved, and (b) v1.1 reused with 0 repairs, all visible in the Process timeline and the Skill library.

---

## Phase 4: SkillSmith, creating new skills with an LLM (5–7 days)

1. **An LLM client** in `backend/app/services/llm.py`:
   - Ollama HTTP (`OLLAMA_URL`, `OLLAMA_MODEL`, for example `qwen2.5-coder` or `llama3.1`), behind a small interface so a hosted API can be swapped in for production.
   - Settings go in `config.py`.
2. **Generate the contract.** From the reviewed requirement plus the CSV headers and preview, ask the LLM for a `SkillContract` as **structured JSON**. Validate it with Pydantic and retry once if it doesn't parse.
3. **Generate the code.** Prompt with the contract, the tool function signatures, two example skills (the sales skill) and the rules (tools only, a pure function, return a dict). Run the Phase 2 static check, then the sandbox.
4. **Generate the tests.** Ask for 3–5 contract checks (types, totals equal the sum of the parts, row-count conservation). Combine them with fixed, built-in checks so the LLM can never mark its own homework alone.
5. **Wire it into the worker:**
   1. Discovery finds no validated skill for the capability.
   2. Run `create`: emit `skill_created` (a `candidate` version).
   3. Run `execute` and `evaluate`, then `repair` (Phase 3, with LLM-assisted repair as a fallback strategy).
   4. Promote the result to `validated`.
6. **Add a second real capability** to prove the system generalises, for example "average order value by month" or "top 5 products by units".
7. **Tests:** mock the LLM client so CI stays deterministic. Add a small number of `@skipUnless(OLLAMA_URL)` live tests.

**Done when** a requirement with no existing skill produces a new validated skill version from scratch, and a second identical request reuses it.

---

## Phase 5: smarter requirement review and discovery (2–3 days)

1. **LLM review with structured output** in `requirement_review.py`:
   - The output is `{capability, required_inputs, clarifying_question?, confidence}`.
   - Keep `keyword_rules_v1` as a fallback when the LLM is unavailable or not confident enough.
2. **Ask clarifying questions.** When confidence is low, set the status to `waiting_input` and add a clarification event. The Process view already handles `waiting_input`.
3. **Capability discovery.** Match the requirement to a registry `capability` by name or synonyms first; add embeddings later if the registry grows.

**Done when** varied wording ("total sales per item", "revenue grouped by product") finds the same skill, and unclear requests ask a question instead of failing.

---

## Phase 6: wire the frontend to the real system (4–5 days)

1. **Live updates.** Add `GET /executions/{id}/stream` (SSE) in FastAPI, and switch `useSkillForgeProcess.js` from `setTimeout` polling to `EventSource`, falling back to polling.
2. **A real Live console.** Replace the scripted `startRun` in `App.jsx` with a real submission that renders real events. Map the event types to the console tags (TASK, FIND, MAKE, RUN, FAIL, PATCH, TEST, SAVE, REUSE).
3. **A repair diff viewer.** In the Skill library card, add "View changes": a side-by-side `parent_version` → `version` diff from `change_json`, plus the failure evidence and test results.
4. **Version lineage.** In the library, show `1.0.0 → 1.1.0 (repaired)`.
5. **Human review.** For `needs_review` runs, add an approval panel: see the proposed repair, then Approve (promote), Edit or Reject. Add the endpoints `POST /executions/{id}/repair/approve` and `/reject`.
6. **Real metrics.** Add `GET /metrics/summary` (skills, success rate, repairs, reuse count, average time) and replace the sample `Metrics` values on the Workbench.
7. **Demo mode.** In `src/api/skillforgeProcess.js`, when the API can't be reached, replay a **recorded real execution** (a JSON fixture) so the public site never shows a dead "Cannot reach SkillForge".
8. **Landing honesty.** Once Phases 3–4 ship, point the hero's "Try it" button at a real demo run.

**Done when** everything the Workbench shows comes from the API (or a clearly labelled demo replay), and repair approval works from the UI.

---

## Phase 7: frontend code health (3–4 days; can run alongside Phase 6)

1. **Split `App.jsx`** into:
   - `src/routes/{Workbench,Library,Console,Activity,Guardrails}.jsx`
   - `src/state/useDemoRun.js`
   - `src/components/{Modal,Topbar,Footer}.jsx`
2. **Consolidate the CSS.** Merge the stacked layers (`styles`, `experience`, `scenes`, `cinematic`, `final-polish`, `workspace-polish`, `unified-motion`, `neutral-theme`, `automatic-motion`) into:
   - `tokens.css` (the palette from `neutral-theme.css`),
   - `base.css`,
   - one CSS file per component.

   Use the browser's coverage tool to delete dead rules. Check every page in dark and light mode after each merge.
3. **Tests:**
   - **Vitest:** `mergeEvents`, the API error handling, and `useSkillForgeProcess` state changes.
   - **Playwright smoke test:** the landing page loads, the Workbench submits a task, Activity lists it, and the theme toggle works.
4. **Accessibility pass:** keyboard navigation, focus rings, labels on the custom controls, contrast in light mode.

**Done when** no source file is over about 500 lines, CI runs Vitest and Playwright, and nothing looks different.

---

## Phase 8: security and guardrails (2–3 days)

1. **Auth:** start with a single-user API token (`Authorization: Bearer`), then move to proper accounts (Supabase Auth or Clerk) with each workspace scoped to its owner. `Workspace` already exists.
2. **Harden the sandbox:** run skills in a throwaway container (Docker, or a microVM such as Vercel Sandbox or Firecracker) with no network and a read-only filesystem.
3. **Limits:** request rate limits, CSV size, row and column limits (already partly in `csv_inputs.py`), and LLM token budgets per workspace.
4. **Production CORS and secrets:** take `FRONTEND_ORIGINS` from the environment, never commit `.env`, and rotate the Postgres password used in development.
5. **Audit trail:** every promotion and approval writes an event with who did it and why.

**Done when** someone without your token can't reach the API, and generated code can't touch the network or the filesystem.

---

## Phase 9: deploy (2 days)

1. **Dockerfiles:** `backend/Dockerfile` (one image; command `uvicorn` for the API, `python -m app.worker` for the worker).
2. **Database:** Neon or Supabase Postgres. Run `alembic upgrade head` on every release.
3. **Backend hosting:** Render or Fly.io, with two processes (api and worker), health checks on `/api/v1/health/ready`, and the env vars from `backend/.env.example`.
4. **LLM:** Ollama needs a GPU or a strong CPU host. For production, either run Ollama on a separate box or point the `llm.py` interface at a hosted model API.
5. **Frontend:** Vercel, with `VITE_API_BASE_URL` set to the deployed API.
6. **Run `register_builtin_skills` on first deploy** (via a one-off job).

**Done when** a public URL runs the full pipeline, and the demo-mode fallback covers any downtime.

---

## Phase 10: launch (1–2 days)

1. **Re-record the promo** using a **real** run. The current video is labelled illustrative; re-render it with the real timeline JSON.
2. **A public "watch a run" page:** a shareable link that replays a stored execution, ideal for X.
3. **Docs:** update the README (remove the "simulated" rows), add architecture docs in `docs/architecture.md` (a sequence diagram of the loop) and an API reference (FastAPI's `/docs`).
4. **Post:** a launch thread on X with the video, the live link and the GitHub repo. Write it up for your portfolio.

---

## Definition of "complete"

- [ ] A brand-new requirement creates a **new skill** (Phase 4)
- [ ] A failing run is **repaired automatically** within a budget, or sent for **human review** (Phases 3 and 6)
- [ ] Every repair produces a **new version** with a diff, evidence and parent link (Phases 2 and 3)
- [ ] The next matching run **reuses** the latest validated version (Phase 3)
- [ ] Generated code runs only in a **sandbox** with approved tools (Phases 2 and 8)
- [ ] The Workbench, console, library and activity show **only real data**, or a labelled replay (Phase 6)
- [ ] CI is green with backend, frontend and end-to-end tests (Phases 1 and 7)
- [ ] It is deployed at a public URL with auth (Phases 8 and 9)

## Rough timeline (solo, part time)

| Week | Phases |
|---|---|
| 1 | 0, 1, and the start of 2 |
| 2 | Finish 2, then 3 (**the real repair loop: the biggest milestone**) |
| 3–4 | 4 (SkillSmith create) and 5 |
| 5 | 6, with 7 alongside |
| 6 | 8, 9, 10: ship it 🚀 |

**If you only do one thing next:** Phase 3. Once a real failure is repaired into v1.1 and reused, the core claim of the project is true.
