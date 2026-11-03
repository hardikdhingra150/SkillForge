# SkillForge

Self-evolving skill infrastructure for AI agents: **build what's missing, repair what breaks, remember what works.**

SkillForge pairs a React workspace (dot-matrix and pixel type on a greyscale particle background, in dark and light themes) with a FastAPI + PostgreSQL backend.

**Chat** with Claude, Codex or a local model. Repeatable tasks become tested, versioned skills that later messages reuse. When a skill fails or gives a wrong answer, SkillSmith repairs it and saves a new version. The **Workbench** runs the same loop on uploaded CSV files.

> **Status:** create, execute, verify, repair, version and reuse all run for real, from chat (any text task) and from the Workbench (CSV sales analysis). The Live console on the Workbench is still a scripted demo. See [PROJECT_COMPLETION_PLAN.md](PROJECT_COMPLETION_PLAN.md).

## What's real and what's simulated

| Area | Status |
|---|---|
| Requirement review (keyword rules, `keyword_rules_v1`) | ✅ Backend |
| CSV upload, column mapping, confirmation, SHA-256 integrity checks | ✅ Backend |
| Queue + background worker, execution timeline events | ✅ Backend |
| Versioned skill registry with validation evidence and implementation hash | ✅ Backend |
| Skills stored as source + contract, run in a sandbox (static policy, approved tools, CPU/time limits, no env or file writes) | ✅ Backend |
| Host-side contract checks against independent reference calculations | ✅ Backend |
| Execution history: search, filter, reopen | ✅ Backend |
| **Chat** with Claude (Claude Code CLI), Codex (Codex CLI) or a local Ollama model | ✅ |
| Planner: answer directly, reuse a skill, or create one | ✅ LLM, structured JSON |
| SkillSmith **creation**: contract, source and worked examples, proven in the sandbox | ✅ |
| Independent **cross-model verifier** (a different model checks the answer) and example arbitration | ✅ |
| **LLM repair** of a skill that crashes or gives a wrong answer, promoted as a new version | ✅ |
| **Escalation** from the local model to a stronger one when it cannot produce a proven skill | ✅ |
| Automatic **repair**: classify the failure, patch the skill, prove it on the failing input + lineage regression fixtures + strategy proof fixtures, promote a new version | ✅ Backend (one strategy so far: `normalize_amounts`) |
| Repair budget, then `waiting_approval` for human review | ✅ Backend (the approval UI is Phase 6) |
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

### Try the pipeline

1. Open **Workbench**.
2. Submit "Show revenue by product".
3. Upload a sales CSV (for example `demo_data/step10_sales.csv`) and confirm the product and revenue columns.
4. Watch the timeline in the Process view. Finished runs appear under **Activity**, and the skill version appears under **Skill library**.

**See a real self-repair:**

1. Run the same task with `demo_data/sales_formatted_amounts.csv`. Its amounts look like `$1,200.50` and `(120.00)`.
2. v1.0.0 fails with `BAD_NUMBER`. The worker patches it to use `parse_amount`, proves the fix, and saves **v1.1.0** (repaired from v1.0.0).
3. Every later run reuses v1.1.0 with no repair. The Skill library shows the diff, the failure it fixed, and the new tests.

`REPAIR_BUDGET` (default `2`, in `backend/.env`) caps the attempts. When none succeeds, the run waits in `waiting_approval` for a person.

### Developer commands

A `Makefile` wraps the common tasks. Run `make help` to list them.

| Command | What it does |
|---|---|
| `make setup` | `npm install`, create `backend/.venv`, install the backend and dev requirements |
| `make db` / `make migrate` / `make seed` | Start Postgres, apply migrations, register the built-in skills |
| `make api` / `make worker` / `make web` | Run the API (:8000), the worker, and the frontend (:5173) |
| `make lint` | Run `ruff` (backend) and ESLint (frontend) |
| `make test` | Backend unit tests |
| `make check` | Lint, tests and the production build: everything CI runs |

### CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push to `main` and on every pull request:

- **Backend:** `ruff check` and the unit tests on Python 3.14.
- **Frontend:** ESLint with zero warnings allowed, then `vite build`.

> A registered skill version is immutable. Its `implementation_hash` covers its stored source and contract, and the worker refuses to run a version whose stored source no longer matches. To change a built-in skill (`backend/app/skills/`), bump its version and run `make seed`.

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
    ChatView.jsx              chat with provider picker, live agent steps, skill result cards
    SkillForgeProcessView.jsx · SkillRegistryView.jsx · ExecutionHistory.jsx · CSVInputPanel.jsx
  *.css                       theme layers (neutral-theme.css holds the palette)
backend/
  app/main.py                 FastAPI app and routers (/api/v1)
  app/worker.py               polling worker: requirement review + execution
  app/services/               requirement_review, csv_inputs, execution_queue, checks, skill_registry, repair, agent
  app/llm/                    providers: Claude Code CLI, Codex CLI, Ollama (status + complete)
  app/api/chat.py             providers, conversations, messages (agent runs in the background)
  app/sandbox/                policy (static checks), tools (approved toolkit), runner + child process
  app/skills/                 built-in skill source files, contracts and fixtures
  app/schemas/skill_contract.py  the contract every stored skill declares
  app/database/               SQLAlchemy models; migrations/ holds Alembic
  tests/                      unittest suites
compose.yaml                  local Postgres
```

## Motion and accessibility

- Decorative motion pauses when it's off screen or the tab is hidden.
- The header has a pause control, and the system "reduce motion" setting is respected; both show all content without animation.
- Byte and Scout follow a mouse pointer on desktop and never intercept input.
