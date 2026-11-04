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
