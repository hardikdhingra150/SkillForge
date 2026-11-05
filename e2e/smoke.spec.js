import { expect, test } from '@playwright/test';

import { mockApi } from './mockApi.js';

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test('the landing page loads', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Every failure becomes a skill.' })).toBeVisible();
});

test('the Workbench submits a task and Activity lists it', async ({ page }) => {
  await page.goto('/#workbench');
  await page.getByPlaceholder('Show revenue by product from my sales data.').fill('Show revenue by product');
  await page.getByRole('button', { name: 'Submit requirement' }).click();
  await expect(page.getByText('Your request has been saved.').first()).toBeVisible();

  await page.getByRole('button', { name: 'Activity' }).first().click();
  await expect(page.getByText('Show revenue by product').first()).toBeVisible();
});

test('the theme toggle switches and remembers light mode', async ({ page }) => {
  await page.goto('/#workbench');
  const html = page.locator('html');
  const before = await html.getAttribute('data-theme');
  const next = before === 'dark' ? 'light' : 'dark';

  await page.getByRole('button', { name: `Switch to ${next} mode` }).click();
  await expect(html).toHaveAttribute('data-theme', next);

  await page.reload();
  await expect(html).toHaveAttribute('data-theme', next);
});

test('the Live console replays a recorded real run when the API is offline', async ({ page }) => {
  await page.unrouteAll();
  await page.route('http://127.0.0.1:5999/api/v1/**', (route) => route.abort());
  await page.goto('/#console');
  await page.getByRole('button', { name: 'Let’s run it' }).click();

  const log = page.getByLabel('Execution log');
  await expect(log.getByText('Saved revenue_by_product v1.1.0 (repaired from v1.0.0).', { exact: false })).toBeVisible({ timeout: 20000 });
  await expect(page.getByText('RECORDED RUN · API OFFLINE')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Replay again' })).toBeVisible({ timeout: 10000 });
});

test('the Review page shows the audit trail', async ({ page }) => {
  await page.goto('/#review');
  const trail = page.getByRole('region', { name: 'Audit trail' });
  await expect(trail.getByText('revenue_by_product@1.1.0')).toBeVisible();
  await expect(trail.getByText('by worker')).toBeVisible();
});
