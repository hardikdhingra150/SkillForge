# Deploy SkillForge for free

This puts SkillForge online at an address anyone can open from Windows, macOS, Linux or a phone, with nothing to install and no server of your own to manage. Every part is on a free plan:

| Part | Free service | What it runs |
|---|---|---|
| **Frontend** | **Vercel** (Hobby) | The web app. Redeploys by itself on every push to GitHub. |
| **Backend** | **Render** (free web service, Docker) | The API and the worker, in one container. Redeploys by itself on every push. |
| **Chat model for visitors** | **Groq** (free API tier, no card) | Fast hosted open models that visitors chat with and that write new skills. |
| **Database** | **Supabase** (free project) | Workspaces, chats, runs and skills. |

Visitors never sign in: each browser automatically gets a private workspace, and workspaces nobody opens for 30 days are deleted. Your own Claude and Codex logins are only for you: you unlock them on the site with your owner key.

The live frontend is already deployed at **https://skillforge-beta-lilac.vercel.app**, and the backend settings are in [`render.yaml`](render.yaml).

## What "free" means in practice

- **The backend sleeps after 15 minutes without visitors.** The next visit wakes it, which takes about a minute and a half. Meanwhile the page says the server is starting and checks again by itself.
- **The free backend has a tenth of a CPU, so it's slow.**
  - Spreadsheet tasks take 30 seconds to a minute.
  - The first repair of a skill can take two minutes.
  - Chat replies are quick, because Groq does the thinking on its own servers.
- **Groq's free tier has rate limits.** If many people chat at once, some get "Groq's free-tier limit was reached, try again in a minute". SkillForge also caps chat at 50 replies per visitor and 500 for everyone together each day.
- **Skills run in the process sandbox, not containers.** Render doesn't let an app start Docker containers. SkillForge checks each skill's code before running it; blocks network, file and process access; gives it no environment variables (so no secrets); and limits its CPU time and memory. That's good protection, but weaker than a container. For container isolation, use your own server (see [Option B](#option-b-your-own-server)).
- **Supabase pauses a free project after a week with no activity**, and has a 500 MB limit. If it pauses, press **Restore** in the Supabase dashboard.

## 1. Database: Supabase (done)

Your `skillforge` project is ready, with all tables and row-level security. You'll need its connection string in step 3: **Connect → Connection String → Type: URI → Method: Session pooler**, with your password filled in (the same line as `DATABASE_URL` in `backend/.env`). Production needs a password of 16+ characters; yours is.

## 2. Chat model: Groq

1. Sign up at <https://console.groq.com> (free, no card).
2. Open **API Keys → Create API Key**, name it `skillforge`, and copy the key (it starts with `gsk_`). You'll paste it in step 3. Keep it private.

## 3. Backend: Render

1. Sign up at <https://render.com> with your GitHub account (free plan).
2. Click **New → Blueprint**, pick the `hardikdhingra150/SkillForge` repository, and click **Connect**. Render reads [`render.yaml`](render.yaml) and shows one service, `skillforge-api`, on the free plan in Singapore (closest to your Supabase database).
3. Render asks for the settings marked `sync: false`. Fill in:

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | Your Supabase session pooler string |
   | `GROQ_API_KEY` | Your Groq key from step 2 |
   | `CLAUDE_CODE_OAUTH_TOKEN` | Optional: see step 5. Leave empty for now. |
   | `CODEX_AUTH_JSON` | Optional: see step 5. Leave empty for now. |

4. Click **Apply**. The first deploy takes 10–15 minutes (building the image, then registering the starter skills). When it says **Live**, open

   `https://skillforge-api.onrender.com/api/v1/health/ready`

   (or the address Render shows, if that name was taken). It should say `"api":"ready","database":"ready"`.

Render created your **owner key** (`API_TOKEN`) for you. To see it, open the service's **Environment** page.

## 4. Connect the frontend to the backend

On Vercel, open the `skillforge` project → **Settings → Environment Variables**, and set:

| Name | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://skillforge-api.onrender.com/api/v1` (your Render address + `/api/v1`) |

Then **Deployments → ⋯ → Redeploy**. The build stops with a clear message if the address is missing or isn't `https://…/api/v1`.

If your Vercel address ever changes, update `FRONTEND_ORIGINS` in Render's **Environment** page to match. The API only accepts browser requests from the addresses listed there.

## 5. Unlock Claude and Codex for yourself (optional)

Render keeps no files between restarts, so your logins go in as secrets in the service's **Environment** page:

| Name | How to get the value |
|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | On your Mac, run `claude setup-token`, sign in, and copy the token it prints. |
| `CODEX_AUTH_JSON` | On your Mac, after `codex login`, copy the whole contents of `~/.codex/auth.json`. Codex may renew this login. If Codex stops working on the site, copy the file again. |

Then, on the site, open **Workspace settings** (the status button, top right) → **Site owner? Use your owner key**, and paste your `API_TOKEN`. In that browser, Claude and Codex now appear in the Studio. Visitors never get them: those subscriptions are for your own use.

## 6. Updating

Push to GitHub. Vercel and Render both redeploy by themselves, and the backend applies any database changes when it starts.

## 7. Let Google find it (Search Console)

1. Open <https://search.google.com/search-console> and add a **URL prefix** property with your Vercel address.
2. Choose **HTML file** verification, put the file Google gives you in this repository's `public/` folder, and push.
3. When Vercel has redeployed, press **Verify**, then submit your address for indexing.

## How it's protected

- **Visitors are kept apart.** Each browser's tasks, chats and history are private. Skills are shared: when anyone's work creates or repairs one, everyone can reuse it, but the visitor's request text and the input that broke it are removed first. Only the owner key can retire, restore or import skills.
- **Spending and load are capped.** Each visitor gets 50 chat replies a day and all visitors together get 500. One address can create at most 30 new workspaces a minute, and requests are rate-limited. Claude and Codex are never available to visitors.
- **Skills are sandboxed**, as described under "What free means in practice".
- **The database is closed to Supabase's public API.** Row-level security is on for every table, and SkillForge connects as the owner.
- **The API only answers your site.** It accepts browser requests only from the addresses in `FRONTEND_ORIGINS`, and it refuses to start in production with unsafe settings.
- **Secrets stay secret.** They live in Render's and Vercel's encrypted settings, never in the repository. The Groq key and your logins go only to the code that calls those services, never to skills. CI scans every push for leaked secrets.

## Other ways to host the backend

- **Hugging Face Spaces** ([`deploy/huggingface/`](deploy/huggingface/)): 16 GB of memory, enough for a local model, but Docker Spaces now need billing on your Hugging Face account.
- <a id="option-b-your-own-server"></a>**Option B, your own server** (for example Oracle Cloud's Always Free VM): [`compose.prod.yaml`](compose.prod.yaml) runs everything with HTTPS through Caddy, and skills run in throwaway containers. Fill in `.env.production` from `.env.production.example`, then run:

  ```bash
  docker compose --env-file .env.production -f compose.prod.yaml up -d --build
  ```
