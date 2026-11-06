// A tiny in-memory SkillForge API for smoke tests: one saved skill and one task the "worker" has reviewed.
const RUN = '0193a8f0-0000-7000-8000-000000000001';
const TASK = '0193a8f0-0000-7000-8000-000000000002';

const CONVERSATION = '0193a8f0-0000-7000-8000-000000000010';

export async function mockApi(page) {
  const runs = [];
  const messages = [];
  const now = new Date().toISOString();
  const conversation = { id: CONVERSATION, title: 'Show revenue by product', provider: 'auto', model: null,
                         created_at: now, updated_at: now };
  const attachment = { id: '0193a8f0-0000-7000-8000-000000000011', filename: 'sample_sales.csv',
                       headers: ['Product', 'Sales', 'OrderDate'], row_count: 5, size_bytes: 180 };

  const execution = (requirement) => ({
    task_id: TASK, execution_id: RUN, requirement, status: 'waiting_input',
    current_stage: 'awaiting_input', created_at: now, plan: null, result: null,
  });

  await page.route('http://127.0.0.1:5999/api/v1/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1', '');
    const json = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

    if (request.method() === 'POST' && path === '/tasks') {
      const { requirement } = request.postDataJSON();
      runs.unshift(execution(requirement));
      return json(runs[0], 201);
    }
    if (path === `/executions/${RUN}` && runs.length) {
      return json(runs[0]);
    }
    if (path === `/executions/${RUN}/events`) {
      return json({
        events: [{
          execution_id: RUN, sequence: 1, stage: 'admission', event_type: 'task_received',
          message: 'Your request has been saved.', payload: {}, created_at: now,
        }],
        next_after: 1,
        has_more: false,
      });
    }
    if (path === '/executions') {
      return json({
        items: runs.map((run) => ({
          execution_id: run.execution_id, task_id: run.task_id, requirement_preview: run.requirement,
          status: run.status, current_stage: run.current_stage, created_at: now, started_at: null, finished_at: null,
        })),
        has_more: false, next_before_created_at: null, next_before_execution_id: null,
      });
    }
    // Studio: one conversation whose spreadsheet request is answered by the reused revenue skill.
    if (path === '/providers') {
      return json([
        { id: 'claude', label: 'Claude (Claude Code CLI)', kind: 'cli', available: false, detail: 'Not logged in.',
          models: [], default_model: null, setup: [] },
        { id: 'ollama', label: 'Local model (Ollama)', kind: 'local', available: false, detail: 'Not running.',
          models: [], default_model: null, setup: [] },
      ]);
    }
    if (path === '/conversations' && request.method() === 'POST') {
      return json(conversation, 201);
    }
    if (path === '/conversations') {
      return json(messages.length ? [conversation] : []);
    }
    if (path === `/conversations/${CONVERSATION}/attachments`) {
      return json(attachment, 201);
    }
    if (path === `/conversations/${CONVERSATION}/messages`) {
      const body = request.postDataJSON();
      messages.push(
        { id: `${CONVERSATION.slice(0, -1)}a`, sequence: 1, role: 'user', content: body.content, status: 'done',
          provider: null, model: null, steps: [], skill: null, attachments: [attachment], created_at: now, updated_at: now },
        { id: `${CONVERSATION.slice(0, -1)}b`, sequence: 2, role: 'assistant', content: 'Reused **revenue_by_product v1.1.0**.',
          status: 'done', provider: 'auto', model: null, attachments: [], created_at: now, updated_at: now,
          steps: [
            { kind: 'spreadsheet', text: 'A spreadsheet task: revenue by product on sample_sales.csv (5 rows). No model is needed to plan it.' },
            { kind: 'columns', text: 'Using product = Product; revenue = Sales.' },
            { kind: 'skill_ran', text: 'Done in 0.4 ms. Reused v1.1.0, no new code needed.' },
          ],
          skill: {
            skill_id: 'revenue_by_product', version: '1.1.0', capability: 'revenue_by_product', origin: 'repaired',
            parent_version: '1.0.0', event: 'reused', contract: {},
            output: { rows_processed: 5, total_revenue: '3658.00', products: [
              { product: 'Backpack', revenue: '2450.00', row_count: 1 },
              { product: 'Notebook', revenue: '1080.50', row_count: 2 },
              { product: 'Pen', revenue: '127.50', row_count: 2 },
            ] },
          } },
      );
      return json(messages, 202);
    }
    if (path === `/conversations/${CONVERSATION}`) {
      return json({ ...conversation, messages });
    }
    if (path === '/workspace/config') {
      return json({ mode: 'off' });
    }
    if (path === '/health/ready') {
      return json({ service: 'skillforge', api: 'ready', database: 'ready' });
    }
    if (path === '/metrics/summary') {
      const succeeded = runs.filter((run) => run.status === 'succeeded').length;
      return json({
        skills: 1, runs: runs.length, succeeded, success_rate: runs.length ? Math.round((100 * succeeded) / runs.length) : null,
        repairs: 0, reuses: 0, created: 0, average_seconds: null,
      });
    }
    if (path === '/skills') {
      return json({
        items: [{
          skill_id: 'revenue_by_product', version: '1.1.0', capability: 'revenue_by_product', status: 'validated',
          implementation_hash: 'x', validation: { passed: true, test_count: 5 }, origin: 'repair', parent_version: '1.0.0',
          contract: { summary: 'Total revenue per product from a sales CSV.' }, change: null, source_code: null, created_at: now,
        }],
        has_more: false, next_after_skill_id: null, next_after_version: null,
      });
    }
    if (path === '/review') {
      return json({ runs: [] });
    }
    if (path === '/audit') {
      return json([{
        id: '0193a8f0-0000-7000-8000-000000000003', actor: 'worker', action: 'skill.promoted',
        target: 'revenue_by_product@1.1.0', reason: "Amounts like '$1,200.50' are export-formatted.",
        details: { strategy: 'normalize_amounts' }, created_at: now,
      }]);
    }
    return json({ detail: 'Not found.' }, 404);
  });
}
