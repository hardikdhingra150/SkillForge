// A tiny in-memory SkillForge API for smoke tests: one saved skill and one task the "worker" has reviewed.
const RUN = '0193a8f0-0000-7000-8000-000000000001';
const TASK = '0193a8f0-0000-7000-8000-000000000002';

export async function mockApi(page) {
  const runs = [];
  const now = new Date().toISOString();

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
