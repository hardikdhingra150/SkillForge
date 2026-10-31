# SkillForge

Self-evolving skill infrastructure for AI agents: **build what's missing, repair what breaks, remember what works.**

SkillForge pairs a React workspace (dot-matrix and pixel type on a greyscale particle background, in dark and light themes) with a FastAPI + PostgreSQL backend. The backend reviews a requirement, takes a CSV input, runs a validated skill from a versioned registry, and records every step.

> **Status:** early. The full backend pipeline works today for one built-in skill (`revenue_by_product`). The **create** and **repair** stages shown on the landing page and in the Live console demo are still simulated in the frontend. See [CHANGES_AND_ROADMAP.md](CHANGES_AND_ROADMAP.md).

## What's real and what's simulated

| Area | Status |
|---|---|
| Requirement review (keyword rules, `keyword_rules_v1`) | ✅ Backend |
| CSV upload, column mapping, confirmation, SHA-256 integrity checks | ✅ Backend |
| Queue + background worker, execution timeline events | ✅ Backend |
| Versioned skill registry with validation evidence and implementation hash | ✅ Backend |
| Execution history: search, filter, reopen | ✅ Backend |
| SkillSmith skill **creation** (LLM / Ollama) | 🚧 Not built yet |
| Automatic **repair** loop and version promotion | 🚧 Not built yet (simulated in the Live console demo) |
| Workbench metrics, crew panel, sample skill cards | 🎭 Sample data |

## Quick start

### Frontend only

The landing page and the demo work without the backend.

```sh
npm install
npm run dev
```

Open <http://127.0.0.1:5173/>. For a production build, run `npm run build`.

### Full stack

**Prerequisites:** Node 20+, Python 3.12+, and Docker (for Postgres).

1. **Environment files.** Copy each example and edit the values:

   ```sh
   cp .env.example .env.local                    # frontend → API URL
   cp .env.postgres.example .env.postgres        # Postgres credentials (set a real password)
   cp backend/.env.example backend/.env          # backend settings
   ```

2. **Start Postgres:**

   ```sh
   docker compose up -d postgres
   ```

3. **Set up the backend**, from `backend/`:

   ```sh
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   alembic upgrade head
   python -m app.register_builtin_skills         # registers revenue_by_product after its self-tests pass
   ```

4. **Run the API and the worker** (two terminals, both in `backend/` with the venv active):

   ```sh
   uvicorn app.main:app --reload --port 8000
   python -m app.worker
   ```

5. **Run the frontend** from the project root with `npm run dev`.

**Health check:** <http://127.0.0.1:8000/api/v1/health/ready>

### Try the pipeline

1. Open **Workbench**.
2. Submit "Show revenue by product".
3. Upload a sales CSV (for example `demo_data/step10_sales.csv`) and confirm the product and revenue columns.
4. Watch the timeline in the Process view. Finished runs appear under **Activity**, and the skill version appears under **Skill library**.

### Tests

Run from `backend/` with the venv active:

```sh
python -m unittest discover tests
```

## Project layout

```text
src/
  App.jsx                     workspace routes, demo run, dialogs, theme
  api/skillforgeProcess.js    API client (VITE_API_BASE_URL)
  hooks/useSkillForgeProcess.js  submit / poll / reopen an execution
  components/
    Landing.jsx               4-section landing page
    HeroForge.jsx             hero + self-playing learning-loop console
    Pop.jsx                   spring pop-in, word reveals, pixel bursts
    ScrollChoreographer.jsx   scroll reveals, parallax, spotlight
    SkillForgeProcessView.jsx · SkillRegistryView.jsx · ExecutionHistory.jsx · CSVInputPanel.jsx
  *.css                       theme layers (neutral-theme.css holds the palette)
backend/
  app/main.py                 FastAPI app and routers (/api/v1)
  app/worker.py               polling worker: requirement review + execution
  app/services/               requirement_review, csv_inputs, execution_queue, builtin_sales
  app/database/               SQLAlchemy models; migrations/ holds Alembic
  tests/                      unittest suites
compose.yaml                  local Postgres
```

## Motion and accessibility

- Decorative motion pauses when it's off screen or the tab is hidden.
- The header has a pause control, and the system "reduce motion" setting is respected; both show all content without animation.
- Byte and Scout follow a mouse pointer on desktop and never intercept input.
