# SkillForge

Self-evolving skill infrastructure for AI agents: **build what's missing, repair what breaks, remember what works.**

SkillForge pairs a React workspace (dot-matrix and pixel type on a greyscale particle background, in dark and light themes) with a FastAPI + PostgreSQL backend.

Everything happens in one place, the **Studio**. Ask anything, or attach a spreadsheet (CSV or Excel) and say what you want from it, and pick the model: Auto, Claude, Codex or a local one.

- **Spreadsheet tasks with a ready-made skill** (revenue by product, totals by a column, totals by month, remove duplicates, clean up a table) run at once with no model: the columns are picked for you and every number is checked against an independent recount.
- **Anything else** (a different question about the file, text, maths, "make a skill that…") gets a new skill: a model writes it, it's tested in the sandbox, another model checks the answer, and it's saved for everyone to reuse.
- **When a skill fails**, the automatic fixes run first (formatted amounts, date formats, renamed columns), then a model rewrites it. The working version is saved as a new version.
- **You see every step**: which skill was reused, created or repaired, and how.

The top navigation has three pages: **Studio**, **Skills** (every saved skill, its versions and tests) and **Models** (what's connected, and how each model has done). Past runs, Review, the Live console, the classic Workbench and Guardrails are linked from the footer.

> **Status:** create, execute, verify, repair, version and reuse all run for real. See [PROJECT_COMPLETION_PLAN.md](PROJECT_COMPLETION_PLAN.md).

## What works today

Everything below runs against the real API and database. Nothing in the app is pre-recorded or sample data; when the API is offline, pages say so and show how to start it.

| Area | Status |
|---|---|
| Requirement review: keyword rules first, then an LLM review (`llm_review_v1`) that understands varied wording | ✅ Backend |
| **Clarifying questions**: an unclear request (Workbench or chat) gets one specific question instead of failing | ✅ |
| **Capability discovery**: "pull emails", "grab every mail address" and `extract_emails` find the same skill (synonyms, then model confirmation) instead of creating near-duplicates | ✅ |
| **Contract-aware verifier**: answers are judged against the skill's documented behaviour and defaults; a wrong input binding is re-bound before any code repair | ✅ |
| **Workbench file workflows**: revenue by product, totals by any column (region, category, store…), totals by month, remove duplicate rows (whole row or by an id/email column), clean up a table (spaces, N/A/null placeholders, empty rows) | ✅ |
| **CSV and Excel (.xlsx)** upload with drag and drop; Excel's first sheet is converted to CSV (zip-bomb and size guards) | ✅ |
| **Suggested columns**: picked from header names, the values themselves and the words in your request, shown preselected for you to confirm | ✅ |
| Column mapping, confirmation, SHA-256 integrity checks | ✅ Backend |
| Queue + background worker, execution timeline events | ✅ Backend |
| Versioned skill registry with validation evidence and implementation hash | ✅ Backend |
| Skills stored as source + contract, run in a sandbox (static policy, approved tools, CPU/time limits, a runtime audit hook that blocks network, process and file access; optional Docker container with no network and a read-only filesystem) | ✅ Backend |
| **Private workspaces, no sign-in** (`AUTH_MODE=browser`): every browser silently gets its own workspace for tasks, chats, reviews, metrics and history. The skill library stays shared, and only the operator's `API_TOKEN` can retire, restore or import skills | ✅ |
| **Hosted database**: point `DATABASE_URL` at Supabase (or any Postgres 17+) instead of running Postgres yourself | ✅ |
| **Ready to host**: skills run in throwaway containers from the Docker setup, new skills are shared with everyone after the visitor's data is removed, idle workspaces are deleted after 30 days, chat has per-visitor and site-wide daily caps, and Claude and Codex are kept for the owner | ✅ |
| **One-command install**: `docker compose up --build` runs Postgres, the API (migrations and starter skills on start), the worker and the web app | ✅ |
| **Security:** bearer-token API access, rate and body-size limits, a daily model budget, safe production settings enforced at startup, and an audit trail of every promotion, rollback, import and review decision | ✅ |
| Host-side contract checks against independent reference calculations | ✅ Backend |
| Execution history: search, filter, reopen | ✅ Backend |
| **Chat** with Claude (Claude Code CLI), Codex (Codex CLI) or a local Ollama model | ✅ |
| **Auto** provider: routes each capability to the cheapest model that has proven itself (model scoreboard) | ✅ |
| **Files in chat**: attach a CSV; file skills such as `revenue_by_product` are reused and repaired | ✅ |
| **Multi-step tasks**: 1–4 chained skills, a step can use an earlier step's output (`$step1.field`) | ✅ |
| **Live streaming** of chat agent steps and Workbench runs over server-sent events, with a polling fallback | ✅ |
| **Live console**: a real task on a bundled sample CSV (fail → repair → v1.1.0 → reuse) | ✅ |
| **Workbench home**: a getting-started checklist that ticks itself off, live API status, latest runs and saved skills; results shown as a table you can download as CSV | ✅ |
| **Landing page**: shows your live workspace (numbers, runs, saved skills), or how to start the API | ✅ |
| Workbench metrics from recorded runs (`GET /metrics/summary`); version lineage in the Skill library | ✅ |
| **Review queue**: retry a run with a bigger repair budget, or reject it; **retire / restore** versions (instant rollback) | ✅ |
| **Export / import** a skill as one JSON bundle; imports are re-proven (hash, sandbox policy, every fixture) | ✅ |
| **MCP server**: validated skills become tools for Claude Code, Codex and Cursor | ✅ |
| Starter skill pack (17): the 5 file workflows plus `extract_emails`, `extract_urls`, `word_stats`, `word_frequency`, `change_case`, `slugify`, `dedupe_list`, `convert_temperature`, `number_stats`, `percent_change`, `roman_numerals`, `loan_payment` | ✅ registered on start (Docker) or `make seed` |
| Planner: answer directly, reuse a skill, or create one | ✅ LLM, structured JSON |
| SkillSmith **creation**: contract, source and worked examples, proven in the sandbox | ✅ |
| Independent **cross-model verifier** (a different model checks the answer) and example arbitration | ✅ |
| **LLM repair** of a skill that crashes or gives a wrong answer, promoted as a new version | ✅ |
| **Escalation** from the local model to a stronger one when it cannot produce a proven skill | ✅ |
| Automatic **repair**: classify the failure, patch the skill, prove it on the failing input + lineage regression fixtures + strategy proof fixtures, promote a new version. Strategies: `normalize_amounts` ($1,200.50, (300), -€100), `normalize_dates` (15/03/2026, 03/15/2026, Mar 15, 2026; day/month order read from the whole column), `match_columns_loosely` ("order_date" finds "Order Date"). When a file has two problems, the second fix builds on the first and both ship as one version | ✅ |
| Repair budget, then `waiting_approval` for human review | ✅ (Review page) |

## Quick start

### Put it online for free

[DEPLOY.md](DEPLOY.md) walks through hosting SkillForge for everyone at no cost and with no server to manage: the frontend on **Vercel**, the backend (API, worker and a local model) on a free **Hugging Face Space**, and the database on **Supabase**. Visitors chat with the local model; your own Claude and Codex logins are kept for you. If you have your own server, `compose.prod.yaml` runs everything there with HTTPS.

### One command (Docker)

**Prerequisites:** Docker. That's all.

```sh
docker compose up --build        # or: make up
```

Open <http://localhost:5173>. The first start builds the images (a few minutes); later starts take seconds. Postgres, the API, the worker and the web app run in containers, the API applies migrations and registers the starter skills, and your data lives in a Docker volume. Stop with `docker compose down` (or `make down`).

- Chat in Docker can use **Ollama** running on your machine. The Claude Code and Codex CLIs run as your user, so use the setup below for those.
- Each browser gets its own private workspace; nobody signs in. For one workspace shared by everyone: `AUTH_MODE=off docker compose up --build`.
- To keep the data in Supabase instead of the Postgres container, see [Use Supabase as the database](#use-supabase-as-the-database).
- Already made a `.env.postgres` for the setup below? Run `docker compose --env-file .env.postgres up --build` (or `make up`, which does this for you) so the passwords match.

### For development (with `make`)

**Prerequisites:** Node 20+, Python 3.12+, Docker, and for Chat at least one of Claude Code CLI, Codex CLI or Ollama.

```sh
cp .env.example .env.local
cp .env.postgres.example .env.postgres        # set a real POSTGRES_PASSWORD
cp backend/.env.example backend/.env
make setup      # npm install + backend virtualenv
make db         # Postgres in Docker
make migrate    # create the tables
make seed       # register the starter skills
make api        # terminal 1
make worker     # terminal 2
make web        # terminal 3, then open http://127.0.0.1:5173/#workbench
```

### Use Supabase as the database

SkillForge works with Supabase's Postgres; the migrations add a `uuidv7()` function on Postgres 17, which Supabase runs.

1. In the Supabase dashboard, open your project and click **Connect**. Copy the **Session pooler** connection string. The direct connection needs IPv6, and the transaction pooler doesn't fit SQLAlchemy's connection pool.
2. Put it in `backend/.env` with your database password in place of `[YOUR-PASSWORD]`. If you don't know the password, reset it under **Project Settings → Database**.
   ```sh
   DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-1-<region>.pooler.supabase.com:5432/postgres
   ```
3. Create the tables and the starter skills, then start as usual:
   ```sh
   cd backend && .venv/bin/alembic upgrade head && .venv/bin/python -m app.register_builtin_skills
   ```

With Docker, put `DATABASE_URL=...` in a `.env` file next to `compose.yaml`; the API applies migrations on start. TLS (`sslmode=require`) is added for any non-local host.

### Frontend only

The landing page opens without the backend; the workspace then shows the commands to start it.

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
   python -m app.register_builtin_skills         # runs each built-in skill's fixtures in the sandbox, then registers it
   ```

4. **Run the API and the worker** (two terminals, both in `backend/` with the venv active):

   ```sh
   uvicorn app.main:app --reload --port 8000
   python -m app.worker
   ```

5. **Run the frontend** from the project root with `npm run dev`.

**Health check:** <http://127.0.0.1:8000/api/v1/health/ready>

### Connect the models (Chat)

Chat uses the command-line tools already installed on your machine, so your own subscriptions are used and no API keys are stored. Each call runs in an empty temporary folder, with tools disabled or a read-only sandbox, and without the app's environment variables.

**Claude** (Claude Code CLI, uses your Claude subscription):

```bash
curl -fsSL https://claude.ai/install.sh | bash   # install Claude Code
claude auth login                                # log in (opens your browser)
claude auth status                               # check: "loggedIn": true
```

**Codex** (OpenAI Codex CLI, uses your ChatGPT plan):

```bash
npm install -g @openai/codex                     # install the Codex CLI
codex login                                      # log in with ChatGPT (opens your browser)
codex login status                               # check: "Logged in using ChatGPT"
```

**Local model** (Ollama, runs offline on your machine):

```bash
brew install ollama                              # install Ollama
ollama serve                                     # start it (leave it running)
ollama pull qwen2.5-coder:3b                     # download the model (about 1.9 GB)
```

The Chat page shows each provider's live status. A provider that isn't connected shows these exact commands with copy buttons; press **Re-check** after you log in.

**How a chat message flows:**
1. The planner decides whether to answer directly or use a skill.
2. If a skill fits, the latest validated version runs in the sandbox, and an independent verifier checks the answer.
3. If no skill fits, SkillSmith writes one. It must reproduce its worked examples in the sandbox and pass the verifier before it's saved.
4. If a skill crashes or gives a wrong answer, SkillSmith rewrites it. The fix must also pass every earlier example, and it's saved as a new version.
5. If the local model can't produce a proven skill, the task escalates to Codex or Claude.

### Use SkillForge skills from other agents (MCP)

Every validated skill becomes an MCP tool. It runs the newest validated version in the sandbox, then the contract checks, and the result includes which version answered. New and repaired skills appear automatically. Postgres must be running (`make db`).

```bash
claude mcp add skillforge -- "$PWD/backend/bin/skillforge-mcp"
```
```bash
codex mcp add skillforge -- "$PWD/backend/bin/skillforge-mcp"
```

For Cursor, add the same command to `~/.cursor/mcp.json` under `mcpServers.skillforge.command`. The Skill library page shows these commands with this machine's paths.

### Model scoreboard and Auto routing

Every proof outcome is recorded per model: proven on the first try, rejected, exhausted, overruled by the verifier, example corrected, reused, escalated. The **Models** page shows the numbers.

With **Auto**:
1. Planning uses the cheapest available model.
2. Each capability goes to the cheapest model that has proven it before.
3. With no history, it tries the cheapest model and escalates to a stronger one on failure, and the router learns from the outcome.
4. The local model never verifies a cloud model's work.

### Try the pipeline

1. Open **Workbench** and click one of the example tasks under the box (or write your own).
2. Drop a CSV or Excel file on the upload area (for example `demo_data/step10_sales.csv`). The columns are suggested for you; check them and confirm.
3. The result appears as a table you can download as CSV.
4. Watch the timeline in the Process view. Finished runs appear under **Activity**, and the skill version appears under **Skill library**.

Wording doesn't have to match: "How much money did each item bring in?" is understood by the LLM review. A vague request such as "Analyze my spreadsheet" gets a question in the Process view; answer it and the run is reviewed again (up to 5 rounds).

**See a real self-repair:**

1. Run the same task with `demo_data/sales_formatted_amounts.csv`. Its amounts look like `$1,200.50` and `(120.00)`.
2. v1.0.0 fails with `BAD_NUMBER`. The worker patches it to use `parse_amount`, proves the fix, and saves **v1.1.0** (repaired from v1.0.0).
3. Every later run reuses v1.1.0 with no repair. The Skill library shows the diff, the failure it fixed, and the new tests.

`REPAIR_BUDGET` (default `2`, in `backend/.env`) caps the attempts. When none succeeds, the run waits in `waiting_approval` for a person.

### Developer commands

A `Makefile` wraps the common tasks. Run `make help` to list them.

| Command | What it does |
|---|---|
| `make up` / `make down` | Run or stop everything in Docker (http://localhost:5173) |
| `make setup` | `npm install`, create `backend/.venv`, install the backend and dev requirements |
| `make db` / `make migrate` / `make seed` | Start Postgres, apply migrations, register the built-in skills |
| `make api` / `make worker` / `make web` | Run the API (:8000), the worker, and the frontend (:5173) |
| `make lint` | Run `ruff` (backend) and ESLint (frontend) |
| `make test` | Backend unit tests and frontend Vitest tests |
| `make e2e` | Playwright smoke and accessibility tests against a mocked API (run `npx playwright install chromium` once) |
| `make check` | Lint, tests and the production build |
| `make token` / `make rotate-db-password` / `make secrets` / `make sandbox-image` | New API token; new local DB password; gitleaks scan; pull the Docker sandbox image |

### CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push to `main` and on every pull request:

- **Backend:** `ruff check` and the unit tests on Python 3.14.
- **Frontend:** ESLint with zero warnings allowed, Vitest, then `vite build`.
- **Docker:** `docker compose config` and a build of the API and web images.
- **Secrets:** gitleaks over the full git history.
- **E2E:** Playwright smoke tests and an axe-core WCAG 2 AA scan of every page in both themes, against a mocked API (traces are uploaded on failure).

> A registered skill version is immutable. Its `implementation_hash` covers its stored source and contract, and the worker refuses to run a version whose stored source no longer matches. To change a built-in skill (`backend/app/skills/`), bump its version and run `make seed`.

## Project layout

```text
src/
  App.jsx                     routing, theme, motion, toasts and modal state (~410 lines)
  navigation.js               the workspace pages and valid #hash routes
  routes/                     Workbench, ConsolePage, Guardrails
  state/useLiveRun.js         the Live console's real sample run
  state/useWorkspace.js       live API status, metrics, latest runs and saved skills
  workflows.js                the Workbench's example tasks
  api/skillforgeProcess.js    API client (VITE_API_BASE_URL), run stream, metrics
  api/liveRun.js              the console's real run: submit, upload the sample CSV, follow events
  hooks/useSkillForgeProcess.js  submit / stream (polling fallback) / reopen an execution
  components/
    Topbar.jsx · Footer.jsx · AppModals.jsx · Modal.jsx · ui.jsx
    Console.jsx · Metrics.jsx · TaskResult.jsx
    WorkspaceHome.jsx         Workbench home: getting-started checklist and live status
    WorkspaceParts.jsx        status pill, setup steps, saved skills
    Landing.jsx               4-section landing page
    HeroForge.jsx             hero + your live workspace (or how to start the API)
    Pop.jsx                   spring pop-in, word reveals, pixel bursts
    ScrollChoreographer.jsx   scroll reveals, parallax, spotlight
    ChatView.jsx              chat: provider picker (Auto…), CSV attachments, live steps, skill/pipeline cards
    ModelsView.jsx · ReviewView.jsx  model scoreboard and routing; human review queue
    SkillForgeProcessView.jsx · SkillRegistryView.jsx · ExecutionHistory.jsx · CSVInputPanel.jsx
  styles/                     global CSS in cascade order: tokens.css (palette), base, workspace,
                              api-views, scroll, landing; component CSS sits next to its component
  **/*.test.js(x)             Vitest unit tests
e2e/                          Playwright smoke + accessibility tests, mockApi.js
backend/
  app/main.py                 FastAPI app and routers (/api/v1)
  app/worker.py               polling worker: requirement review + execution
  app/services/               workflows (file workflows, column suggestions), requirement_review, csv_inputs (CSV + Excel),
                              execution_queue, checks, skill_registry, repair, browser_workspaces, agent,
                              scoreboard (routing), live (SSE), skill_bundle (export/import)
  app/mcp_server.py           MCP server (stdio): validated skills as tools; launcher in backend/bin/skillforge-mcp
  app/api/review.py           review queue, retire/restore versions
  app/llm/                    providers: Claude Code CLI, Codex CLI, Ollama (status + complete)
  app/api/chat.py             providers, conversations, messages (agent runs in the background)
  app/sandbox/                policy (static checks), tools (approved toolkit), runner + child process
  app/skills/                 built-in skill source files, contracts and fixtures
  app/schemas/skill_contract.py  the contract every stored skill declares
  app/database/               SQLAlchemy models; migrations/ holds Alembic
  tests/                      unittest suites
compose.yaml                  the whole stack (Postgres, API, worker, web); `make db` starts only Postgres
backend/Dockerfile · Dockerfile.web   images for the API/worker and the web app
```

## Security

| Guard | How |
|---|---|
| Workspaces | `AUTH_MODE=browser`: on its first request a browser is answered 401, asks `POST /api/v1/workspace/browser` for a new workspace and keeps the random `sfb_…` key it gets in local storage. The server stores only the key's SHA-256. Every query is scoped to the key's workspace, and new workspaces are limited to 30 per address per minute. Clearing the browser's data or using another device starts a new, empty workspace; there is no way to move one between browsers. |
| API access | Set `API_TOKEN` (`make token`) and every `/api/v1` route except the health checks needs `Authorization: Bearer <token>`. Paste the token under **Workspace settings** (the gear button); it's kept in that browser only. The run and chat streams accept `?access_token=` instead, because EventSource can't send headers, and the logs redact it. With no token the API stays open in development and closed in production. |
| Sandbox | Static policy (no imports, no dunders, no `open`) → child process with `python -I -S`, an empty environment and CPU, file and process limits → a Python audit hook that raises on sockets, subprocesses, file writes, reads outside the stdlib, and ctypes. `SANDBOX_BACKEND=docker` (`make sandbox-image`) adds a throwaway container: `--network none`, `--read-only`, `--cap-drop ALL`, `no-new-privileges`, user `nobody`, 32 PIDs, 256 MB. |
| Limits | Per client: 60 writes and 600 reads per minute (`RATE_LIMIT_*`, then 429 with `Retry-After`). Request bodies up to 2 MiB. CSVs up to 1 MiB, 10,000 rows, 50 columns; Excel files up to 5 MiB (80 MiB unpacked) and the same limits once converted. `CHAT_TURNS_PER_DAY` (200) agent replies per workspace. |
| Production | With `APP_ENV=production`, the API refuses to start without `AUTH_MODE=browser` or `API_TOKEN`, without `SANDBOX_BACKEND=docker`, with non-https or `*` origins, or with a weak or default Postgres password. |
| Audit trail | Every promotion (worker or agent), retire, restore, import, retry and reject writes an `audit_events` row: who, what, why, details. Read it on the **Review** page or at `GET /api/v1/audit`. |
| Secrets | `.env` files are git-ignored. CI runs gitleaks over the full history (`make secrets` locally). `make rotate-db-password` sets a new local Postgres password in the database and `.env.postgres`. |

The MCP server talks to the database directly over stdio on your machine, so it isn't behind the API token. Only run it locally.

## Motion and accessibility

- Decorative motion pauses when it's off screen or the tab is hidden.
- The header has a pause control, and the system "reduce motion" setting is respected; both show all content without animation.
- Byte and Scout follow a mouse pointer on desktop and never intercept input.
- Animated headings split text into `aria-hidden` pieces and keep one screen-reader copy of the full text.
- Every page passes an axe-core WCAG 2 AA scan in dark and light mode (`make e2e`), and the header is keyboard navigable with visible focus rings.
