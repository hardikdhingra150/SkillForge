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
  await page.getByRole('button', { name: 'Start task', exact: true }).click();
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

test('the Live console says when the API is offline instead of replaying anything', async ({ page }) => {
  await page.unrouteAll();
  await page.route('http://127.0.0.1:5999/api/v1/**', (route) => route.abort());
  await page.goto('/#console');
  await page.getByRole('button', { name: 'Run the sample' }).click();

  const log = page.getByLabel('Execution log');
  await expect(log.getByText('Can’t reach the SkillForge API.', { exact: false })).toBeVisible();
  await expect(page.getByText('START THE API TO RUN')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible();
});

test('the Review page shows the audit trail', async ({ page }) => {
  await page.goto('/#review');
  const trail = page.getByRole('region', { name: 'Audit trail' });
  await expect(trail.getByText('revenue_by_product@1.1.0')).toBeVisible();
  await expect(trail.getByText('by worker')).toBeVisible();
});
