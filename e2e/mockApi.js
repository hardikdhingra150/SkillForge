// A tiny in-memory SkillForge API for smoke tests: one task that the "worker" has reviewed.
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
    return json({ detail: 'Not found.' }, 404);
  });
}
