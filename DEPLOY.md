# Deploy SkillForge for free

This puts SkillForge on the internet at an `https://` address anyone can open from Windows, macOS, Linux or a phone, with nothing to install. Every part is on a free plan:

| Part | Free service | What it does |
|---|---|---|
| Server | Oracle Cloud **Always Free** VM (4 ARM cores, 24 GB RAM) | Runs the web app, API, worker, the local model and the skill sandbox |
| Database | **Supabase** free project | Stores workspaces, runs, chats and skills |
| Address | **DuckDNS** subdomain, such as `myskillforge.duckdns.org` | Points a name at your server |
| HTTPS | **Caddy** with Let's Encrypt | Gets and renews the certificate by itself |
| Chat for visitors | **Ollama** on the server | A local model, so no per-message bill |
| Chat for you | Your own **Claude Code** and **Codex** logins | Only you can use them, with your owner key |

Visitors never sign in: each browser automatically gets a private workspace. Workspaces nobody opens for 30 days are deleted.

## What "free" costs you in practice

- **Oracle asks for a card** to verify you, but Always Free resources are never charged. If Oracle says a shape is "out of capacity", try another availability domain or try again later.
- **Oracle may reclaim an idle Always Free VM** (very low CPU use for 7 days). A live site normally stays busy enough. Upgrading the account to "Pay As You Go" stops reclaiming and still costs $0 while you stay inside the free limits.
- **Supabase pauses a free project after a week with no activity**, and has a 500 MB limit. The worker connects all the time, which counts as activity; if it does pause, press **Restore** in the dashboard.
- **The local model is slower than Claude.** On 4 ARM cores, a chat reply from `qwen2.5-coder:3b` takes tens of seconds. Workbench file tasks don't use a model and stay fast.

## 1. Create the server (Oracle Cloud)

1. Sign up at <https://www.oracle.com/cloud/free/> and choose a **home region** near your users. You can't change it later.
2. Go to **Compute → Instances → Create instance**:
   - **Image:** Canonical Ubuntu 24.04.
   - **Shape:** Ampere `VM.Standard.A1.Flex` with **4 OCPUs and 24 GB** memory (the whole free allowance).
   - **SSH keys:** download the private key it generates, or paste your own public key.
3. When it's running, copy its **Public IP address**.
4. Open the web ports. In the instance's **Subnet → Security List**, add two ingress rules: source `0.0.0.0/0`, TCP, destination ports `80` and `443`.
5. Ubuntu on Oracle also blocks them in its own firewall. Connect and open them there too:

   ```bash
   ssh -i your-key ubuntu@YOUR_SERVER_IP
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
   sudo netfilter-persistent save
   ```

## 2. Get a free address (DuckDNS)

1. Sign in at <https://www.duckdns.org> (with GitHub or Google).
2. Add a subdomain, for example `myskillforge`, and set its **current ip** to the server's public IP.
3. Your site will be `https://myskillforge.duckdns.org`.

## 3. Prepare the database (Supabase)

SkillForge creates its own tables when it starts. Two things to check:

1. The database password must be **at least 16 characters** for production. If yours is shorter, reset it in **Project Settings → Database → Reset database password**. Use only letters and numbers.
2. Copy the connection string from **Connect → Connection String → Type: URI → Method: Session pooler**, and put your password into it.

## 4. Install and start SkillForge on the server

On the server:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
git clone https://github.com/hardikdhingra150/SkillForge.git && cd SkillForge
cp .env.production.example .env.production
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # this is your owner key
nano .env.production
```

In `.env.production`, fill in:

- `SITE_DOMAIN`: your DuckDNS name, without `https://`.
- `DATABASE_URL`: the Supabase session pooler string from step 3.
- `API_TOKEN`: the owner key the command above printed. Keep it somewhere safe; it unlocks Claude and Codex in chat.

Start everything:

```bash
docker compose --env-file .env.production -f compose.prod.yaml up -d --build
```

The first start takes 10–20 minutes: it builds the images and downloads the local model (about 1.9 GB). Check progress with:

```bash
docker compose --env-file .env.production -f compose.prod.yaml ps
docker compose --env-file .env.production -f compose.prod.yaml logs -f api
```

Then open `https://YOUR_SITE_DOMAIN`. The first visit can take a few seconds while Caddy gets the certificate.

## 5. Connect your own Claude and Codex (optional, owner only)

Log in once inside the server. The logins are kept in a Docker volume, so rebuilds keep them:

```bash
docker compose --env-file .env.production -f compose.prod.yaml exec api claude auth login
docker compose --env-file .env.production -f compose.prod.yaml exec api codex login
```

Each prints a link: open it on your own computer, sign in, and paste back any code it asks for.

Then, on the site, open **Workspace settings** (the status button, top right) → **Site owner? Use your owner key**, and paste your `API_TOKEN`. That browser now uses the owner's workspace, where Claude and Codex appear in Chat. Visitors only ever see the local model.

## 6. Update to a new version

```bash
cd SkillForge && git pull
docker compose --env-file .env.production -f compose.prod.yaml up -d --build
```

Database changes are applied automatically when the API starts.

## 7. Let Google find it (Search Console)

1. Open <https://search.google.com/search-console> and add a **URL prefix** property: `https://YOUR_SITE_DOMAIN`.
2. Choose **HTML file** verification and download the file Google gives you.
3. Put it in the repository's `public/` folder, commit it, and update the server (step 6).
4. Press **Verify** in Search Console, then submit `https://YOUR_SITE_DOMAIN/` for indexing.

## How it's protected

- **Skills run in throwaway containers** with no network, a read-only filesystem, no capabilities, an unprivileged user and CPU, memory and process limits. The API and worker start them through a proxy that only allows the Docker calls `docker run` needs.
- **Visitors are kept apart.** Each browser's tasks, chats and history are private. Skills are shared: when anyone's Chat creates or repairs one, everyone can reuse it, but the visitor's request text and the input that broke it are removed first. Only the owner key can retire, restore or import skills.
- **Spending and load are capped.** Each visitor gets 50 chat replies a day, and all visitors together get 500 (`CHAT_TURNS_PER_DAY`, `CHAT_TURNS_PER_DAY_TOTAL`). One address can create at most 30 new workspaces a minute, and requests are rate-limited.
- **The database is closed to Supabase's public API.** Row-level security is on for every table, and SkillForge connects as the owner.
- **Secrets stay on the server.** `.env.production` is ignored by git, and CI scans every push for leaked secrets.

The Docker proxy still lets the API create containers. If someone broke into the API process itself, they could use that to reach the host. Keep the server updated (`sudo apt upgrade`), and don't run anything else important on it.
