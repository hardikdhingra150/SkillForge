# Deploy SkillForge for free

This puts SkillForge online at an address anyone can open from Windows, macOS, Linux or a phone, with nothing to install and no server of your own to manage. Every part is on a free plan:

| Part | Free service | What it runs |
|---|---|---|
| **Frontend** | **Vercel** (Hobby) | The web app. Redeploys by itself on every push to GitHub. |
| **Backend** | **Hugging Face Spaces** (Docker, "CPU basic": 2 CPUs, 16 GB RAM) | The API, the worker and the local model visitors chat with, in one container. |
| **Database** | **Supabase** (free project) | Workspaces, chats, runs and skills. |

Visitors never sign in: each browser automatically gets a private workspace, and workspaces nobody opens for 30 days are deleted. Visitors chat with the free local model. Your own Claude and Codex logins are only for you: you unlock them on the site with your owner key.

## What "free" means in practice

- **The backend sleeps after 48 hours without visitors.** The next visit wakes it, which takes a minute or two, and the page says the API is starting until then.
- **Visitors' chat replies are slow** (one to three minutes), because the free machine has no GPU. Spreadsheet tasks with a ready-made skill don't use a model and finish in seconds.
- **Skills run in the process sandbox, not containers.** Hugging Face doesn't let an app start Docker containers. SkillForge checks each skill's code before running it; blocks network, file and process access; gives it no environment variables (so no secrets); and limits its CPU time and memory. That's good protection, but weaker than a container. For container isolation, use your own server (see [Option B](#option-b-your-own-server)).
- **Supabase pauses a free project after a week with no activity**, and has a 500 MB limit. The worker uses the database all the time, which counts as activity; if it does pause, press **Restore** in the Supabase dashboard.

## 1. Database: Supabase

You already have the `skillforge` project. Two things:

1. **Set a strong password.** Production needs a database password of **16+ characters**. Reset it under **Project Settings → Database → Reset database password**, using only letters and numbers.
2. **Copy the connection string:** **Connect → Connection String → Type: URI → Method: Session pooler**. Replace `[YOUR-PASSWORD]` with your password. Keep this string private.

## 2. Backend: Hugging Face Space

1. Sign up at <https://huggingface.co/join> (free, no card).
2. Click **New → Space**:
   - **Space name:** `skillforge-api`.
   - **SDK:** **Docker** → **Blank**.
   - **Hardware:** **CPU basic · free**.
   - **Visibility:** **Public**, so the web app can reach it. Your secrets stay hidden either way.
3. In the new Space, open **Files → Add file → Upload files**, and upload the two files from this repository's [`deploy/huggingface/`](deploy/huggingface/) folder: `Dockerfile` and `README.md`. Commit them. That's all the Space needs: the build fetches SkillForge from GitHub.
4. Open **Settings → Variables and secrets** and add:

   | Name | Type | Value |
   |---|---|---|
   | `DATABASE_URL` | Secret | The Supabase session pooler string from step 1 |
   | `API_TOKEN` | Secret | Your owner key. Make one on your Mac with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` and keep it safe |
   | `FRONTEND_ORIGINS` | Variable | `["https://skillforge.vercel.app"]`, your Vercel address from step 3. Set it now with your best guess and correct it after step 3 |

5. The Space builds by itself. The first build takes 15–25 minutes, because it downloads the local model (about 1.9 GB) into the image. When the status says **Running**, open

   `https://YOUR-HF-USERNAME-skillforge-api.hf.space/api/v1/health/ready`

   It should say `"api":"ready","database":"ready"`. The address is also under the Space's **⋮ → Embed this Space**.

## 3. Frontend: Vercel

1. Sign in at <https://vercel.com> with GitHub (Hobby plan, free).
2. **Add New → Project**, then import `hardikdhingra150/SkillForge`. Vercel reads the settings from `vercel.json`.
3. Before deploying, open **Environment Variables** and add:

   | Name | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://YOUR-HF-USERNAME-skillforge-api.hf.space/api/v1` |

   The build stops with a clear message if this is missing or doesn't start with `https://` and end with `/api/v1`.
4. Click **Deploy**. Your site is at `https://<project>.vercel.app` (shown when the deploy finishes).
5. If that address differs from what you put in `FRONTEND_ORIGINS` in step 2, update the variable in the Space's settings and restart it. The API only accepts requests from the addresses listed there.

Open your Vercel address. The status pill at the top right should say **Connected**.

## 4. Unlock Claude and Codex for yourself (optional)

The Space has no disk that survives restarts, so your logins go in as secrets. Add them in the Space's **Settings → Variables and secrets**, then restart it:

| Name | Type | How to get the value |
|---|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | Secret | On your Mac, run `claude setup-token`, sign in, and copy the token it prints. |
| `CODEX_AUTH_JSON` | Secret | On your Mac, after `codex login`, copy the whole contents of `~/.codex/auth.json`. Codex may renew this login. If Codex stops working on the site, copy the file again. |

Then, on the site, open **Workspace settings** (the status button, top right) → **Site owner? Use your owner key**, and paste your `API_TOKEN`. In that browser, Claude and Codex now appear in the Studio. Visitors only ever get the local model. Your Claude and Codex subscriptions are for your own use, which is why they are never offered to visitors.

## 5. Updating

- **Frontend:** push to GitHub. Vercel redeploys by itself.
- **Backend:** in the Space, **Settings → Factory rebuild**. It fetches the latest code from GitHub. Database changes are applied when it starts.

## 6. Let Google find it (Search Console)

1. Open <https://search.google.com/search-console> and add a **URL prefix** property with your Vercel address.
2. Choose **HTML file** verification, put the file Google gives you in this repository's `public/` folder, and push.
3. When Vercel has redeployed, press **Verify**, then submit your address for indexing.

## How it's protected

- **Visitors are kept apart.** Each browser's tasks, chats and history are private. Skills are shared: when anyone's work creates or repairs one, everyone can reuse it, but the visitor's request text and the input that broke it are removed first. Only the owner key can retire, restore or import skills.
- **Spending and load are capped.** Each visitor gets 50 chat replies a day, and all visitors together get 500. One address can create at most 30 new workspaces a minute, and requests are rate-limited. Claude and Codex are never available to visitors.
- **Skills are sandboxed**, as described under "What free means in practice".
- **The database is closed to Supabase's public API.** Row-level security is on for every table, and SkillForge connects as the owner.
- **The API only answers your site.** It accepts browser requests only from the addresses in `FRONTEND_ORIGINS`, and it refuses to start in production with unsafe settings.
- **Secrets stay secret.** They live in the Space's encrypted secrets and Vercel's environment variables, never in the repository. CI scans every push for leaked secrets.

## Option B: your own server

If you later have a Linux server (for example Oracle Cloud's Always Free VM), [`compose.prod.yaml`](compose.prod.yaml) runs everything there with one command: the web app, API, worker, the local model and HTTPS through Caddy. Skills then run in throwaway containers. Fill in `.env.production` from `.env.production.example` (`SITE_DOMAIN`, `DATABASE_URL`, `API_TOKEN`), then run:

```bash
docker compose --env-file .env.production -f compose.prod.yaml up -d --build
```
