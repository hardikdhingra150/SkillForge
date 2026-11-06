# Deploy SkillForge for free

This puts SkillForge online at an address anyone can open from Windows, macOS, Linux or a phone, with nothing to install and no server of your own to manage. Every part is on a free plan:

| Part | Free service | What it runs |
|---|---|---|
| **Frontend** | **Vercel** (Hobby) | The web app. Redeploys by itself on every push to GitHub. |
| **Backend** | **Render** (free web service, Docker) | The API and the worker, in one container. Redeploys by itself on every push. |
| **Database** | **Supabase** (free project) | Workspaces, chats, runs and skills. |

Visitors never sign in: each browser automatically gets a private workspace, and workspaces nobody opens for 30 days are deleted. For chat and new skills, visitors connect **their own** Claude Code or Codex from their computer (see [Visitors' own Claude and Codex](#visitors-own-claude-and-codex)). Spreadsheet tasks need no model at all. Your own Claude and Codex logins on the server are only for you: you unlock them on the site with your owner key.

**It's live:** the frontend at **https://skillforge-beta-lilac.vercel.app** talks to the backend at **https://skillforge-api-0n0y.onrender.com**, which uses the Supabase database. The backend settings are in [`render.yaml`](render.yaml).

## What "free" means in practice

- **The backend sleeps after 15 minutes without visitors.** The next visit wakes it, which takes about a minute and a half. Meanwhile the page says the server is starting and checks again by itself.
- **The free backend has a tenth of a CPU, so it's slow.**
  - Spreadsheet tasks take 30 seconds to a minute.
  - The first repair of a skill can take two minutes.
  - Chat replies take as long as the visitor's own Claude or Codex takes, because the thinking happens on their computer.
- **Chat is capped** at 50 replies per visitor and 500 for everyone together each day.
- **Skills run in the process sandbox, not containers.** Render doesn't let an app start Docker containers. SkillForge checks each skill's code before running it; blocks network, file and process access; gives it no environment variables (so no secrets); and limits its CPU time and memory. That's good protection, but weaker than a container. For container isolation, use your own server (see [Option B](#option-b-your-own-server)).
- **Supabase pauses a free project after a week with no activity**, and has a 500 MB limit. If it pauses, press **Restore** in the Supabase dashboard.

## 1. Database: Supabase (done)

Your `skillforge` project is ready, with all tables and row-level security. You'll need its connection string in step 2: **Connect → Connection String → Type: URI → Method: Session pooler**, with your password filled in (the same line as `DATABASE_URL` in `backend/.env`). Production needs a password of 16+ characters; yours is.

## 2. Backend: Render

1. Sign up at <https://render.com> with your GitHub account (free plan).
2. Click **New → Blueprint**, pick the `hardikdhingra150/SkillForge` repository, and click **Connect**. Render reads [`render.yaml`](render.yaml) and shows one service, `skillforge-api`, on the free plan in Singapore (closest to your Supabase database).
3. Render asks for the settings marked `sync: false`. Fill in:

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | Your Supabase session pooler string |
   | `CLAUDE_CODE_OAUTH_TOKEN` | Optional: see step 4. Leave empty for now. |
   | `CODEX_AUTH_JSON` | Optional: see step 4. Leave empty for now. |

4. Click **Apply**. The first deploy takes 10–15 minutes (building the image, then registering the starter skills). When it says **Live**, open

   `https://skillforge-api.onrender.com/api/v1/health/ready`

   (or the address Render shows, if that name was taken). It should say `"api":"ready","database":"ready"`.

Render created your **owner key** (`API_TOKEN`) for you. To see it, open the service's **Environment** page.

## 3. Connect the frontend to the backend

On Vercel, open the `skillforge` project → **Settings → Environment Variables**, and set:

| Name | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://skillforge-api.onrender.com/api/v1` (your Render address + `/api/v1`) |

Then **Deployments → ⋯ → Redeploy**. The build stops with a clear message if the address is missing or isn't `https://…/api/v1`.

If your Vercel address ever changes, update `FRONTEND_ORIGINS` in Render's **Environment** page to match. The API only accepts browser requests from the addresses listed there.

## 4. Unlock Claude and Codex for yourself (optional)

Render keeps no files between restarts, so your logins go in as secrets in the service's **Environment** page:

| Name | How to get the value |
|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | On your Mac, run `claude setup-token`, sign in, and copy the token it prints. |
| `CODEX_AUTH_JSON` | On your Mac, after `codex login`, copy the whole contents of `~/.codex/auth.json`. Codex may renew this login. If Codex stops working on the site, copy the file again. |

Then, on the site, open **Workspace settings** (the status button, top right) → **Site owner? Use your owner key**, and paste your `API_TOKEN`. In that browser, Claude and Codex now appear in the Studio. Visitors never get them: those subscriptions are for your own use.

## Visitors' own Claude and Codex

Visitors can use their own Claude Code or Codex subscription, without giving SkillForge their login:

1. In the Studio, a visitor picks **Claude** or **Codex** and clicks **Connect your computer**.
2. The Studio shows one command (for macOS/Linux and for Windows). They run it in a terminal and leave it open. It needs Python 3, plus Claude Code or Codex installed and logged in on that computer.
3. While it runs, that visitor's chats send their Claude and Codex requests to their computer. Their own logged-in CLI answers, with its tools switched off (Claude) or in its read-only sandbox (Codex), in an empty folder.

The server never uses its own logins for visitors, and never sees the visitor's login. Each workspace has its own connector key, stored only as a hash; **Disconnect** in the Studio revokes it, and the program stops. While a connector is running it contacts the site every 20 seconds, which also keeps Render's free backend awake.

## 5. Updating

Push to GitHub. Vercel and Render both redeploy by themselves, and the backend applies any database changes when it starts.

## 6. Let Google find it (Search Console)

1. Open <https://search.google.com/search-console> and add a **URL prefix** property with your Vercel address.
2. Choose **HTML file** verification, put the file Google gives you in this repository's `public/` folder, and push.
3. When Vercel has redeployed, press **Verify**, then submit your address for indexing.

## How it's protected

- **Visitors are kept apart.** Each browser's tasks, chats and history are private. Skills are shared: when anyone's work creates or repairs one, everyone can reuse it, but the visitor's request text and the input that broke it are removed first. Only the owner key can retire, restore or import skills.
- **Spending and load are capped.** Each visitor gets 50 chat replies a day and all visitors together get 500. One address can create at most 30 new workspaces a minute, and requests are rate-limited. Claude and Codex are never available to visitors.
- **Skills are sandboxed**, as described under "What free means in practice".
- **The database is closed to Supabase's public API.** Row-level security is on for every table, and SkillForge connects as the owner.
- **The API only answers your site.** It accepts browser requests only from the addresses in `FRONTEND_ORIGINS`, and it refuses to start in production with unsafe settings.
- **Secrets stay secret.** They live in Render's and Vercel's encrypted settings, never in the repository. Your logins go only to the Claude and Codex command-line tools, never to skills. CI scans every push for leaked secrets.

## Other ways to host the backend

- **Hugging Face Spaces** ([`deploy/huggingface/`](deploy/huggingface/)): 16 GB of memory, enough for a local model, but Docker Spaces now need billing on your Hugging Face account.
- <a id="option-b-your-own-server"></a>**Option B, your own server** (for example Oracle Cloud's Always Free VM): [`compose.prod.yaml`](compose.prod.yaml) runs everything with HTTPS through Caddy, and skills run in throwaway containers. Fill in `.env.production` from `.env.production.example`, then run:

  ```bash
  docker compose --env-file .env.production -f compose.prod.yaml up -d --build
  ```
