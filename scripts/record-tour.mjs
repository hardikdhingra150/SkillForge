/* global document, window, requestAnimationFrame */
// Records the SkillForge tour video (public/tour/skillforge-tour.webm) by driving the real web app in a browser.
//
//   node scripts/record-tour.mjs
//
// The app runs against a scripted demo backend (the browser tests' mock API plus the scenes below), so every
// scene plays the same way and nothing waits on a real model. Captions and a visible cursor are drawn on the page.
import { spawn } from 'node:child_process';
import { mkdir, readdir, rename, rm } from 'node:fs/promises';
import { setTimeout as sleep } from 'node:timers/promises';
import { chromium } from '@playwright/test';

import { mockApi } from '../e2e/mockApi.js';

const PORT = 5190;
const APP = `http://127.0.0.1:${PORT}`;
const API = 'http://127.0.0.1:5999/api/v1';
const OUT = new URL('../public/tour/', import.meta.url).pathname;
const SIZE = { width: 1280, height: 720 };
const now = () => new Date().toISOString();

// ---------- the demo backend's scenes ----------

const SAMPLE = { id: '0193a8f0-0000-7000-8000-0000000000a1', filename: 'sample_sales.csv',
  headers: ['Product', 'Sales', 'OrderDate'], row_count: 5, size_bytes: 180 };

const step = (kind, text) => ({ kind, text, payload: {}, at: now() });

const SCENES = [
  {
    match: /revenue by product/i,
    provider: 'auto',
    content: 'Reused **revenue_by_product v1.1.0**.',
    steps: [
      step('spreadsheet', 'A spreadsheet task: revenue by product on sample_sales.csv (5 rows). No model is needed to plan it.'),
      step('columns', 'Using product = Product; revenue = Sales.'),
      step('skill_selected', 'Found revenue_by_product v1.1.0 in the registry. Running it in the sandbox.'),
      step('skill_ran', 'Done in 1.7 ms. Reused v1.1.0, no new code needed.'),
    ],
    skill: { skill_id: 'revenue_by_product', version: '1.1.0', capability: 'revenue_by_product', origin: 'repaired',
      parent_version: '1.0.0', event: 'reused', contract: {},
      output: { rows_processed: 5, total_revenue: '3658.00', products: [
        { product: 'Backpack', revenue: '2450.00', row_count: 1 },
        { product: 'Notebook', revenue: '1080.50', row_count: 2 },
        { product: 'Pen', revenue: '127.50', row_count: 2 },
      ] } },
  },
  {
    match: /monthly/i,
    provider: 'auto',
    content: 'Repaired **totals_by_month** and saved **v1.1.0**.',
    steps: [
      step('spreadsheet', 'A spreadsheet task: totals by month on sample_sales.csv (5 rows). No model is needed to plan it.'),
      step('columns', 'Using date = OrderDate; amount = Sales.'),
      step('skill_selected', 'Found totals_by_month v1.0.0 in the registry. Running it in the sandbox.'),
      step('skill_failed', "v1.0.0 failed on this input: dates like '15/03/2026' are not ISO dates."),
      step('repair_started', 'Diagnosed BAD_DATE. Starting repair (budget: 2 attempts).'),
      step('repair_candidate', 'Attempt 1: normalize_dates. Read the column with parse_dates, which works out the day/month order.'),
      step('repair_applied', 'The patched skill passed 5 tests and all contract checks.'),
      step('skill_promoted', 'Saved totals_by_month v1.1.0 (repaired from v1.0.0). Future runs will reuse it.'),
    ],
    skill: { skill_id: 'totals_by_month', version: '1.1.0', capability: 'totals_by_month', origin: 'repaired',
      parent_version: '1.0.0', event: 'repaired', contract: {},
      output: { rows_processed: 5, total: '3658.00', periods: [
        { period: '2026-03', total: '1245.50', row_count: 2 },
        { period: '2026-04', total: '2412.50', row_count: 3 },
      ] } },
  },
  {
    match: /average/i,
    provider: 'claude',
    content: 'Created a new skill, **average_by_group v1.0.0**, and ran it.',
    steps: [
      step('planning', 'Planning with Claude (your computer)…'),
      step('planned', 'A reusable skill: average_by_group.'),
      step('no_skill', 'No skill can do average_by_group yet. SkillSmith will create one.'),
      step('smith', 'SkillSmith attempt 1: writing average_by_group.'),
      step('verifying', 'Independent verifier (Codex (your computer)) is recomputing the answer…'),
      step('verified', 'Verifier agrees with the output.'),
      step('skill_created', 'Created average_by_group v1.0.0: passed 3 examples in the sandbox. Saved to the registry for reuse.'),
    ],
    skill: { skill_id: 'average_by_group', version: '1.0.0', capability: 'average_by_group', origin: 'generated',
      parent_version: null, event: 'created', contract: {},
      output: { groups: [
        { group: 'Backpack', average: '2450.00', count: 1 },
        { group: 'Notebook', average: '540.25', count: 2 },
        { group: 'Pen', average: '63.75', count: 2 },
      ] } },
  },
];

const STEP_MS = 1100;

function skillsPage() {
  const base = { status: 'validated', implementation_hash: 'x', source_code: 'def run(inputs, tools): ...', created_at: now(),
    validation: { passed: true, test_count: 4, tests: [{ name: 'fixture', passed: true }] } };
  return [
    { ...base, skill_id: 'average_by_group', version: '1.0.0', capability: 'average_by_group', origin: 'generated',
      parent_version: null, contract: { summary: 'Average of a number column for each group.' }, change: null },
    { ...base, skill_id: 'clean_table', version: '1.0.0', capability: 'clean_table', origin: 'builtin',
      parent_version: null, contract: { summary: 'Tidy a table: trim spaces, clear placeholders, drop empty rows.' }, change: null },
    { ...base, skill_id: 'revenue_by_product', version: '1.1.0', capability: 'revenue_by_product', origin: 'repaired',
      parent_version: '1.0.0', contract: { summary: 'Total revenue per product from a sales file.' },
      change: { strategy: 'normalize_amounts', summary: 'Amounts like "$1,200.50" are export-formatted: parse them with parse_amount.',
        failure: { code: 'BAD_NUMBER', message: '' },
        diff: '-    revenue = Decimal(row[revenue_column])\n+    revenue = tools.parse_amount(row[revenue_column])' } },
    { ...base, skill_id: 'totals_by_month', version: '1.1.0', capability: 'totals_by_month', origin: 'repaired',
      parent_version: '1.0.0', contract: { summary: 'Totals of an amount column per month.' },
      change: { strategy: 'normalize_dates', summary: 'Dates like 15/03/2026 are read with parse_dates.',
        failure: { code: 'BAD_DATE', message: '' },
        diff: '-    month = row[date_column][:7]\n+    month = tools.iso_dates(column)[i][:7]' } },
  ];
}

const SCOREBOARD = {
  providers: [
    { provider: 'claude', success_rate: 0.94, first_try_rate: 0.81, skills_proven: 17, avg_attempts: 1.2, overruled: 1,
      examples_corrected: 3, escalated_away: 0, reuses: 42, verifier_agree_rate: 0.97, verifier_checks: 31 },
    { provider: 'codex', success_rate: 0.9, first_try_rate: 0.76, skills_proven: 12, avg_attempts: 1.4, overruled: 2,
      examples_corrected: 2, escalated_away: 1, reuses: 27, verifier_agree_rate: 0.95, verifier_checks: 22 },
    { provider: 'ollama', success_rate: 0.62, first_try_rate: 0.4, skills_proven: 5, avg_attempts: 2.1, overruled: 4,
      examples_corrected: 1, escalated_away: 3, reuses: 9, verifier_agree_rate: null, verifier_checks: 0 },
  ],
  capabilities: [
    { capability: 'average_by_group', providers: { claude: { proven: 1, reused: 0 } }, routed_to: 'claude' },
    { capability: 'extract_emails', providers: { codex: { proven: 2, reused: 6 } }, routed_to: 'codex' },
    { capability: 'slugify', providers: { ollama: { proven: 1, exhausted: 1 }, claude: { proven: 1 } }, routed_to: 'claude' },
  ],
};

async function demoBackend(page) {
  await mockApi(page);
  const conversations = new Map();
  let paired = 0;

  const provider = (id) => {
    const connected = paired && Date.now() - paired > 4000;
    const name = id === 'claude' ? 'Claude' : 'Codex';
    return connected
      ? { id, label: `${name} (your computer)`, kind: 'connector', available: true,
        detail: 'Running on your computer, with your login.',
        models: id === 'claude' ? ['default', 'sonnet', 'opus', 'haiku'] : ['default'], default_model: 'default', setup: [] }
      : { id, label: `${name} (your computer)`, kind: 'connector', available: false,
        detail: `Connect your own ${name} from your computer.`, models: [], default_model: null, setup: [] };
  };

  const view = (state) => {
    const messages = [];
    for (const turn of state.turns) {
      messages.push(turn.user);
      const shown = Math.min(turn.scene.steps.length, Math.floor((Date.now() - turn.started) / STEP_MS) + 1);
      const done = shown >= turn.scene.steps.length && Date.now() - turn.started > turn.scene.steps.length * STEP_MS;
      messages.push({
        id: turn.replyId, sequence: turn.user.sequence + 1, role: 'assistant', provider: turn.scene.provider, model: null,
        status: done ? 'done' : 'pending', steps: turn.scene.steps.slice(0, shown), attachments: [],
        content: done ? turn.scene.content : '', skill: done ? turn.scene.skill : null, created_at: now(), updated_at: now(),
      });
    }
    return { ...state.conversation, messages };
  };

  await page.route(`${API}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1', '');
    const json = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
    const method = request.method();

    if (path === '/providers') return json([provider('claude'), provider('codex')]);
    if (path === '/scoreboard') return json(SCOREBOARD);
    if (path === '/skills') return json({ items: skillsPage(), has_more: false, next_after_skill_id: null, next_after_version: null });
    if (path === '/mcp/config') return json({ clients: [], notes: 'Use your saved skills from other AI agents over MCP.' });
    if (path === '/connector' && method === 'POST') {
      paired = Date.now();
      const token = 'sfc_demo-key-shown-once';
      const base = 'https://skillforge-api-0n0y.onrender.com/api/v1';
      return json({ token, connected: false, models: [], commands: {
        mac_linux: `curl -fsSL ${base}/connector.py -o skillforge-connect.py && python3 skillforge-connect.py --api ${base} ${token}`,
        windows: `iwr ${base}/connector.py -OutFile skillforge-connect.py; python skillforge-connect.py --api ${base} ${token}`,
      } }, 201);
    }
    if (path === '/connector') return json({ connected: Boolean(paired && Date.now() - paired > 4000), models: [] });
    if (path === '/conversations' && method === 'POST') {
      const id = `0193a8f0-0000-7000-8000-${String(conversations.size + 100).padStart(12, '0')}`;
      conversations.set(id, { conversation: { id, title: 'New chat', provider: 'auto', model: null, created_at: now(), updated_at: now() }, turns: [] });
      return json(conversations.get(id).conversation, 201);
    }
    if (path === '/conversations') return json([...conversations.values()].map((s) => s.conversation));
    const match = path.match(/^\/conversations\/([^/]+)(\/attachments|\/messages|\/stream)?$/);
    if (match && conversations.has(match[1])) {
      const state = conversations.get(match[1]);
      if (match[2] === '/attachments') return json(SAMPLE, 201);
      if (match[2] === '/stream') return route.fulfill({ status: 404, body: '' });
      if (match[2] === '/messages') {
        const body = request.postDataJSON();
        const scene = SCENES.find((s) => s.match.test(body.content)) || SCENES[0];
        const sequence = state.turns.length * 2 + 1;
        if (!state.turns.length) state.conversation.title = body.content;
        state.turns.push({ scene, started: Date.now(), replyId: `${match[1].slice(0, -4)}r${String(sequence).padStart(3, '0')}`,
          user: { id: `${match[1].slice(0, -4)}u${String(sequence).padStart(3, '0')}`, sequence, role: 'user', content: body.content,
            status: 'done', provider: null, model: null, steps: [], skill: null, created_at: now(), updated_at: now(),
            attachments: body.attachment_ids?.length ? [SAMPLE] : [] } });
        return json(view(state).messages.slice(-2), 202);
      }
      return json(view(state));
    }
    return route.fallback();
  });
}

// ---------- on-screen captions and cursor ----------

function overlay() {
  const css = `
    #tour-caption { position: fixed; left: 50%; bottom: 28px; transform: translateX(-50%); z-index: 2147483647;
      width: min(880px, calc(100vw - 48px)); padding: 16px 22px; border-radius: 16px; pointer-events: none;
      background: rgba(12,12,12,.88); color: #f2f2f2; box-shadow: 0 18px 50px rgba(0,0,0,.45);
      font: 16px/1.45 'Space Grotesk', system-ui, sans-serif; transition: opacity .35s, transform .35s; }
    #tour-caption b { display: block; margin-bottom: 4px; color: #c8ff3d; font: 600 12px/1 ui-monospace, monospace;
      letter-spacing: 1.6px; text-transform: uppercase; }
    #tour-caption.hidden { opacity: 0; transform: translateX(-50%) translateY(12px); }
    #tour-cursor { position: fixed; z-index: 2147483647; width: 22px; height: 22px; margin: -11px 0 0 -11px;
      border-radius: 50%; background: rgba(200,255,61,.85); box-shadow: 0 0 0 4px rgba(200,255,61,.25);
      pointer-events: none; transition: transform .15s; left: -40px; top: -40px; }
    #tour-cursor.down { transform: scale(.7); }
    #tour-card { position: fixed; inset: 0; z-index: 2147483646; display: grid; place-items: center; text-align: center;
      background: #0d0d0d; color: #f2f2f2; font-family: 'Space Grotesk', system-ui, sans-serif; transition: opacity .6s; }
    #tour-card h1 { margin: 0 0 12px; font: 400 64px/1.05 'Pixelify Sans', 'Space Grotesk', sans-serif; }
    #tour-card p { margin: 0; color: #a8a8a8; font-size: 20px; }
    #tour-card small { display: block; margin-top: 26px; color: #c8ff3d; font: 13px ui-monospace, monospace; letter-spacing: 2px; }
    #tour-card.hidden { opacity: 0; pointer-events: none; }
    .cursor-companions { display: none !important; }`;
  const install = () => {
    if (document.getElementById('tour-caption')) return;
    const style = document.createElement('style');
    style.textContent = css;
    document.head.append(style);
    const caption = Object.assign(document.createElement('div'), { id: 'tour-caption', className: 'hidden' });
    const cursor = Object.assign(document.createElement('div'), { id: 'tour-cursor' });
    document.body.append(caption, cursor);
    window.addEventListener('mousemove', (e) => { cursor.style.left = `${e.clientX}px`; cursor.style.top = `${e.clientY}px`; }, true);
    window.addEventListener('mousedown', () => cursor.classList.add('down'), true);
    window.addEventListener('mouseup', () => cursor.classList.remove('down'), true);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
}

// ---------- recording helpers ----------

let page;

async function caption(title, text, hold = 3200) {
  await page.evaluate(([t, x]) => {
    const el = document.getElementById('tour-caption');
    if (!el) return;
    el.innerHTML = '';
    const b = document.createElement('b');
    b.textContent = t;
    el.append(b, document.createTextNode(x));
    el.classList.remove('hidden');
  }, [title, text]);
  await sleep(hold);
}

async function hideCaption() {
  await page.evaluate(() => document.getElementById('tour-caption')?.classList.add('hidden'));
}

async function card(title, text, note, hold = 3800) {
  await page.evaluate(([t, x, n]) => {
    let el = document.getElementById('tour-card');
    if (!el) {
      el = Object.assign(document.createElement('div'), { id: 'tour-card' });
      document.body.append(el);
    }
    el.innerHTML = '';
    const box = document.createElement('div');
    const h = document.createElement('h1');
    h.textContent = t;
    const p = document.createElement('p');
    p.textContent = x;
    const s = document.createElement('small');
    s.textContent = n;
    box.append(h, p, s);
    el.append(box);
    el.classList.remove('hidden');
  }, [title, text, note]);
  await sleep(hold);
  await page.evaluate(() => document.getElementById('tour-card')?.classList.add('hidden'));
  await sleep(700);
}

async function moveTo(locator) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  const target = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
  await page.mouse.move(target.x, target.y, { steps: 28 });
  await sleep(250);
}

async function click(locator) {
  await moveTo(locator);
  await page.mouse.down();
  await sleep(90);
  await page.mouse.up();
  await sleep(500);
}

async function typeInto(locator, text) {
  await click(locator);
  await locator.pressSequentially(text, { delay: 45 });
  await sleep(400);
}

async function scrollBy(dy, steps = 18) {
  for (let i = 0; i < steps; i += 1) {
    await page.mouse.wheel(0, dy / steps);
    await sleep(35);
  }
  await sleep(500);
}

async function waitForReply() {
  await page.waitForFunction(() => {
    const replies = document.querySelectorAll('.sf-chat__message[data-role="assistant"]');
    return replies.length && replies[replies.length - 1].dataset.status === 'done';
  }, null, { timeout: 60000 });
  await sleep(600);
}

async function scrollThreadToEnd() {
  await page.evaluate(() => new Promise((resolve) => {
    const thread = document.querySelector('.sf-chat__thread');
    if (!thread) return resolve();
    const start = thread.scrollTop;
    const end = thread.scrollHeight;
    const t0 = performance.now();
    const tick = (t) => {
      const k = Math.min(1, (t - t0) / 900);
      thread.scrollTop = start + (end - start) * (1 - (1 - k) ** 3);
      if (k < 1) requestAnimationFrame(tick); else resolve();
    };
    requestAnimationFrame(tick);
  }));
  await sleep(400);
}

// ---------- the tour ----------

async function tour() {
  await page.goto(APP);
  await page.waitForLoadState('networkidle');
  await card('SkillForge', 'Ask in plain words. Get a tested skill that does it, and keeps doing it.', 'A TWO-MINUTE TOUR');

  await caption('Home', 'SkillForge turns requests into small, tested programs called skills. When a skill breaks, it repairs itself and saves the fix for next time.', 4200);
  await scrollBy(700);
  await caption('How it works', 'Find a skill, run it in a locked sandbox, check the answer, repair it if needed, and save the version that works.', 3800);
  await scrollBy(-700);
  await click(page.getByRole('button', { name: 'Open Studio' }));

  await caption('The Studio', 'Everything happens here: ask a question, give a task, or attach a spreadsheet. No account needed: this browser gets its own private workspace.', 4600);
  await moveTo(page.locator('.sf-chat__providers'));
  await caption('Pick a model', 'Auto chooses for you. Claude and Codex are your own, connected from your computer, more on that in a moment.', 3800);
  await moveTo(page.getByRole('button', { name: 'Attach spreadsheet' }));
  await caption('Attach a spreadsheet', 'CSV or Excel. Drag a file onto the box, or use this button. Here we use the sample sales file.', 3400);
  await click(page.getByRole('button', { name: 'Try it with a sample sales file' }));
  await caption('Ready-made spreadsheet tasks', 'Revenue by product, totals by a column, totals by month, remove duplicates, clean up a table. They need no AI model at all.', 4200);

  await click(page.getByRole('button', { name: 'Show revenue by product' }));
  await caption('Watch every step', 'SkillForge picks the columns itself, finds a saved skill and runs it in the sandbox.', 3000);
  await waitForReply();
  await scrollThreadToEnd();
  await caption('A tested result', 'Every number is checked against an independent recount. Download the table as CSV.', 3600);
  await moveTo(page.getByRole('button', { name: 'Download CSV' }).last());
  await sleep(1200);
  await page.screenshot({ path: `${OUT}poster.jpg`, type: 'jpeg', quality: 82 });

  await typeInto(page.getByRole('textbox', { name: 'Message' }), 'Monthly sales totals');
  await page.keyboard.press('Enter');
  await caption('When a skill breaks, it repairs itself', 'This file writes dates like 15/03/2026. The skill fails, SkillForge diagnoses why, patches it, tests it, and saves v1.1.0.', 4200);
  await waitForReply();
  await scrollThreadToEnd();
  await caption('Saved for everyone', 'The repaired version is reused next time, by you and by every other user. Nothing has to be fixed twice.', 4000);

  await click(page.getByRole('radio', { name: 'Claude' }));
  await caption('Use your own Claude Code or Codex', 'SkillForge runs them on your computer, with your own login, never on the server.', 3800);
  await click(page.getByRole('button', { name: 'Connect your computer' }));
  await caption('One command', 'Copy it into a terminal on your computer and leave it open. It needs Python 3 and Claude Code or Codex logged in. Tools stay switched off.', 5200);
  await page.waitForSelector('.sf-chat__connect', { state: 'detached', timeout: 20000 });
  await caption('Connected', 'Claude and Codex now answer from your computer. Disconnect any time.', 3200);

  await typeInto(page.getByRole('textbox', { name: 'Message' }), 'What is the average sale per product in this file?');
  await page.keyboard.press('Enter');
  await caption('No skill yet? It writes one', 'Your Claude plans and writes a new skill, your Codex checks the answer independently, and the sandbox tests it.', 4500);
  await waitForReply();
  await scrollThreadToEnd();
  await caption('A new skill, saved', 'average_by_group v1.0.0 is now in the shared library, ready for the next person who asks.', 3800);

  await click(page.getByRole('button', { name: 'Skills' }).first());
  await caption('Skills', 'Every saved skill and every version: what it does, its tests, and whether it was built in, created or repaired.', 4200);
  await scrollBy(520);
  await caption('See what changed', 'Repaired versions show the exact fix and the failure it solved. You can download a skill as a bundle.', 4200);

  await click(page.getByRole('button', { name: 'Models' }).first());
  await caption('Models', 'A scoreboard built from real results: which model writes skills that pass, and which one Auto should route to.', 4600);

  await click(page.getByRole('button', { name: 'Workspace settings and connection' }));
  await caption('Your workspace', 'Private to this browser, with no sign-in. The site owner can unlock their own models here with the owner key.', 4600);
  await page.keyboard.press('Escape');
  await sleep(600);

  await click(page.getByRole('button', { name: /Switch to light/ }));
  await caption('Light or dark', 'Switch themes any time. The footer has past runs, review, the live console and guardrails.', 3600);
  await click(page.getByRole('button', { name: /Switch to dark/ }));
  await hideCaption();

  await card('Every failure becomes a skill.', 'Open the Studio and try it with the sample file.', 'SKILLFORGE', 4200);
}

// ---------- main ----------

async function waitForServer(url, ms = 60000) {
  const until = Date.now() + ms;
  while (Date.now() < until) {
    try {
      if ((await fetch(url)).ok) return;
    } catch { /* not up yet */ }
    await sleep(500);
  }
  throw new Error(`The app didn't start at ${url}.`);
}

const vite = spawn('npx', ['vite', '--host', '127.0.0.1', '--port', String(PORT), '--strictPort'], {
  env: { ...process.env, VITE_API_BASE_URL: API }, stdio: 'ignore',
});
try {
  await waitForServer(APP);
  await mkdir(OUT, { recursive: true });
  const raw = `${OUT}raw/`;
  await rm(raw, { recursive: true, force: true });
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: SIZE, recordVideo: { dir: raw, size: SIZE } });
  await context.addInitScript(() => {
    try { window.localStorage.setItem('skillforge.apiToken', 'sfb_demo-browser-workspace'); } catch { /* ignore */ }
    try { window.localStorage.setItem('skillforge-theme', 'dark'); } catch { /* ignore */ }
  });
  await context.addInitScript(overlay);
  page = await context.newPage();
  await demoBackend(page);
  await tour();
  await context.close();
  await browser.close();
  const [video] = await readdir(raw);
  await rename(`${raw}${video}`, `${OUT}skillforge-tour.webm`);
  await rm(raw, { recursive: true, force: true });
  console.log(`Saved ${OUT}skillforge-tour.webm and poster.jpg`);
} finally {
  vite.kill();
}
