# SkillForge: changes so far and what to build next

_Last updated: 1 November 2026_

This file covers two things:

1. **What changed:** every frontend change made in the Claude Code session, commit by commit.
2. **What to build next:** an honest look at where the project stands, and a prioritised roadmap.

---

## 1. Changes made in the Claude Code session

Four pieces of work: three commits pushed to `main`, plus the promo video. Your own later commits (`15aff32 changed the code`, `1ffdc3f upadying the mock data`) are listed at the end for context but were not part of this session.

### Commit `8eaa457`: scroll animations across the site, and theme matching

**Goal:** every section animates as you scroll, without changing the graphite/silver theme.

| File | Change |
|---|---|
| `src/components/ScrollChoreographer.jsx` | **New.** One scroll engine for every page. It reveals sections once as they enter the viewport (fade, rise, flip, scale, headline wipe, curtain), staggers sibling cards, and sets scroll-position CSS variables for parallax. It also adds the cursor spotlight on cards and the magnetic main buttons. Everything turns off when motion is paused or "reduce motion" is set. |
| `src/components/ScrollStory.jsx` | **New.** A reading-progress bar at the top of the page and the chapter rail on the right of the landing page. |
| `src/scroll-choreography.css` | **New.** Styles for all of the above. The entrances use separate translate/scale/rotate properties so they don't fight the existing floating animations. |
| `src/frontend-harmony.css` | **New.** Restyles the Process, Skill library and Activity views (which had their own blue/grey palette) to match the site: glass panels, Space Mono labels, Pixelify headings, grey status labels. The Process view becomes a full-width two-column panel. |
| `src/App.jsx` | Mounts the scroll engine and the progress bar. The same commit also included your earlier uncommitted change that connects `ExecutionHistory` to the Activity page and the reopen-in-workbench flow. |
| `src/main.jsx` | Imports the new stylesheets. |
| `.claude/launch.json` | **New.** Dev-server config for the in-app preview. |

### Commit `037cdad`: new landing hero

| File | Change |
|---|---|
| `src/components/HeroForge.jsx` | **New.** A centred hero: an announcement pill, the headline "Every failure becomes a **SKILL.**" with Scout, the pitch line, "Open your workspace", and a "Try it" demo button. The centrepiece is a self-playing console that replays one run of the 7-stage learning loop: a stage row, log lines typed out, and a live skill card that tracks the diff, the 3 tests and the result. The console tilts flat as you scroll and pauses when off screen. |
| `src/hero-forge.css` | **New.** Hero styles, the animations that play when the page loads, and the phone/tablet layouts. |
| `src/components/Landing.jsx` | Uses the new hero. |
| `ScrollChoreographer.jsx` / `scroll-choreography.css` | The hero no longer waits for the scroll reveal, which fixed hero text that sometimes loaded faded or blank. |

### Commit `cbfdd88`: a shorter landing page with pop-in animations

| File | Change |
|---|---|
| `src/components/Landing.jsx` | Rewritten as four sections: **Hero → How it learns (3 cards) → Guardrails + stats → Final call to action.** Removed the "Inside the forge" section, the 7-step walkthrough, the domain tabs, the guardrail card grid and the scrolling word band. |
| `src/components/Pop.jsx` | **New.** `Pop` (springs its contents in once on scroll), `PopWords` (headings appear word by word), `Burst` (pixel sparks fly out) and `useInView`. |
| `src/landing-lx.css` | **New.** Spring entrances with overshoot. Pets hop out of the top of each card. Each card plays a small looping demo: code typing, a repair diff with tests, and a version bump. Also the rule pills, the count-up stats and the final card. |
| `src/components/HeroForge.jsx` | Stats moved out of the hero; `CountUp` is now exported for reuse. |
| `src/App.jsx` | The top navigation points to the new sections: How it learns, Guardrails, Get started. |
| `MotionVisibility.jsx`, `ScrollChoreographer.jsx`, `ScrollStory.jsx`, `scroll-choreography.css` | Removed the scroll rules and styles for the deleted sections. |

### Promo video (not part of a code commit)

- `outputs/skillforge-promo.mp4`: 46 seconds, 1920×1080, 30 fps, H.264, about 15 MB, no audio.
- **Scenes:** hook → title → build / repair / remember → the 7-stage loop with a live console → six workspace tiles → guardrails and stats → tech stack → logo and GitHub call to action.
- **How it was made:** a time-driven HTML page rendered frame by frame in headless Chrome and encoded with ffmpeg. Both tools were installed only in a temporary scratch folder, not in the project.
- You committed the video yourself later, in `15aff32`.

### Your own commits after the session (for context)

- `15aff32 changed the code`: a large rework of `App.jsx` (now about 2,600 lines), the API client, the process hook, ExecutionHistory and its CSS. It also added the promo MP4 to git.
- `1ffdc3f upadying the mock data`: expanded the API client and `Landing.jsx`, and committed Python `__pycache__` files.

---

## 2. Where the project stands

### What is real

- **Backend:** FastAPI and PostgreSQL (via `compose.yaml`) with Alembic migrations, and a separate polling worker (`python -m app.worker`).
- **Full pipeline for one task:** you submit a requirement, it is reviewed, you upload a CSV and confirm the column mapping, then the job is queued, executed, validated and the result stored.
  - Every step writes an event to the timeline.
  - The input's SHA-256 hash is checked against what was confirmed.
  - The skill version's implementation hash is checked against the registry.
- **Versioned skill registry:** each version stores its validation evidence and implementation hash, and can be browsed and filtered.
- **Execution history:** search, filter by status, and reopen any run.
- **34 backend tests** across four files: requirement review, CSV inputs, the skill registry and the built-in sales skill.
- **Frontend:** a polished, themed React app with dark and light modes, motion that pauses when off screen, and a pause control and reduced-motion support throughout.

### What is still simulated (the main gap)

The landing page, the console demo and the promo video all promise **create → evaluate → repair → version → reuse**. In the backend today:

| Promise | Reality |
|---|---|
| Discover a skill | ✅ Real, but there is only **one** registered skill (`revenue_by_product`). |
| Create a new skill (SkillSmith) | ❌ Not implemented. There's no code generation and no Ollama call anywhere in `backend/app`. |
| Evaluate a candidate | ⚠️ Partly. The output of the built-in skill is validated, but there's no test suite generated for a new candidate. |
| Repair what breaks | ❌ Not implemented. A failure ends the run as `failed`; there's no repair loop or repair budget. |
| Promote a new version | ❌ Not done automatically. Versions are registered by hand with `register_builtin_skills.py`. |
| Understand the requirement | ⚠️ Keyword rules (`keyword_rules_v1`) recognise only "revenue by product". |

The revenue/Sales repair story in the UI is a frontend script (`startRun` in `App.jsx`), not a backend run.

### Repository hygiene

- **25 compiled Python files (`__pycache__/*.pyc`) are committed.** `.gitignore` doesn't exclude `__pycache__/`, `.venv/`, `.env` or `outputs/`.
- **`backend/.env` and `.env.local` are tracked.** They contain no secrets today (only the app name, environment, allowed origins and database host/port), but the next password added there would be pushed to GitHub.
- **A 15 MB MP4 is in git history.** Large binaries in history slow every clone. Use Git LFS, or host the video elsewhere.
- **The README is out of date.** It still says "no backend is needed" and describes the old seven-stage walkthrough.

### Code health

- `src/App.jsx` is about **2,600 lines** and holds routing, demo state, modals and every workspace view.
- There are **about 13 stacked stylesheets**: `styles`, `experience`, `scenes`, `cinematic`, `final-polish`, `workspace-polish`, `unified-motion`, `neutral-theme`, `automatic-motion`, plus the four added in this session. Later files override earlier ones, so it's hard to know which rule wins.
- **No frontend tests and no CI.** Nothing runs `pytest` or `vite build` on push.
- **No deployment.** The project runs only on your machine.

---

## 3. What to build next (prioritised)

### ⭐ Recommended next step: make the demo real

Build the actual **repair loop** for the exact story the site and video tell, so the marketing becomes a working feature:

1. **Introduce the failure on purpose.** Register `revenue_by_product` v1.0 so that it expects a `revenue` column.
2. **Run it against a CSV whose column is `Sales`.** It fails validation with an `OUTPUT_VALIDATION_FAILED` or `KeyError` event.
3. **Add a `repair` stage to `execution_queue.py`:**
   - Inspect the CSV headers and propose a column alias (`revenue → Sales`). Start with deterministic matching and add the LLM later.
   - Re-run the skill's self-tests and the output validation.
   - Cap attempts with a **repair budget** (for example 2 tries) and emit `repair_started`, `repair_applied` and `repair_exhausted` events.
4. **On success, promote v1.1** to `SkillVersion` with the repair diff, test results and parent version stored in `validation_json`.
5. **On the next run, select v1.1 automatically**, with no repair needed.

This touches only code you already have (`execution_queue.py`, `builtin_sales.py`, `skill_models.py` and a migration), and the timeline UI already shows any event type. After this, the console demo can switch from the scripted run to a real one.

### P0: do these first

| # | Task | Why |
|---|---|---|
| 1 | **Repo cleanup:** add `__pycache__/`, `*.pyc`, `.venv/`, `.env`, `backend/.env`, `.env.local` and `outputs/*.mp4` to `.gitignore`, then `git rm -r --cached` the caches and env files | Stops leaking future secrets and junk files |
| 2 | **Real repair loop** (above) | Closes the biggest gap between what's promised and what works |
| 3 | **Update the README:** how to run the backend, worker and frontend, and what's real versus simulated | Contributors and recruiters read it first |

### P1: next

| # | Task | Notes |
|---|---|---|
| 4 | **SkillSmith create step with Ollama:** given a requirement and a contract, generate a candidate skill, run it with only the approved tools, and test it | Start with one new capability (for example "average order value by month") to prove skills aren't hard-coded |
| 5 | **Requirement review with an LLM:** structured JSON output, falling back to the current keyword rules | Lets the app understand more than one phrase |
| 6 | **Live progress over server-sent events (SSE)** instead of the current `setTimeout` polling in `useSkillForgeProcess` | The timeline feels instant and the server does less work |
| 7 | **Demo mode** in the API client: when the backend can't be reached, play a recorded run | The live site stays impressive without a server and stops showing "Cannot reach SkillForge" |
| 8 | **Deploy:** frontend on Vercel, backend and worker on Render or Fly, Postgres on Neon or Supabase | A public link for the X post and your portfolio |

### P2: code health

| # | Task |
|---|---|
| 9 | Split `App.jsx` into `routes/` (Workbench, Library, Console, Activity, Guardrails) plus `state/useDemoRun.js` |
| 10 | Merge the stacked stylesheets into a single token file plus one stylesheet per component, and delete the dead rules |
| 11 | Add GitHub Actions to run `pytest` and `npm run build` on every push |
| 12 | Add frontend tests: Vitest for the hooks and API client, and a Playwright smoke test (landing loads, workbench submits, history opens) |

### P3: features that would make it stand out

- **Version diff viewer:** a side-by-side diff of v1.0 and v1.1 in the Skill library, with the repair reason and test evidence.
- **Live dashboard:** replace the sample metrics (skills, success rate, repairs) with real counts from Postgres.
- **Skill import and export:** download a validated skill (code, contract and tests) as a bundle, and import it into another workspace.
- **Repair budget and approvals:** when the budget runs out, pause for a human to approve, edit or reject the repair. This makes the guardrails promise concrete.
- **Public "watch a run" page:** a shareable link that replays a real stored execution timeline, ideal for posting on X.

---

## 4. Suggested order for the next two weeks

1. **Day 1:** repo cleanup and README update.
2. **Days 2–5:** the real repair loop, its migration and tests, and the console wired to real events.
3. **Days 6–7:** demo mode and deployment, then post the live link with the promo video.
4. **Week 2:** the SkillSmith create step with Ollama for a second capability, plus CI.
