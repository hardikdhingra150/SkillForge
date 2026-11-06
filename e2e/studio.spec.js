import { expect, test } from '@playwright/test';

import { mockApi } from './mockApi.js';

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test('the Studio runs a spreadsheet task and shows how it was done', async ({ page }) => {
  await page.goto('/#chat');
  await expect(page.getByRole('heading', { name: 'Studio' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Attach spreadsheet' })).toBeVisible();

  await page.getByRole('button', { name: 'Try it with a sample sales file' }).click();
  await expect(page.getByText('sample_sales.csv').first()).toBeVisible();
  await page.getByRole('button', { name: 'Show revenue by product' }).click();

  await expect(page.getByText('No model is needed to plan it.', { exact: false })).toBeVisible();
  await expect(page.getByText('An existing skill did this. No new code.')).toBeVisible();
  const result = page.getByRole('region', { name: 'Result' });
  await expect(result.getByText('3,658.00')).toBeVisible();
  await expect(result.getByRole('rowheader', { name: 'Backpack' })).toBeVisible();
  await expect(result.getByRole('button', { name: 'Download CSV' })).toBeVisible();
});

test('the home page sample opens the Studio and runs there', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Try it with a sample file' }).first().click();
  await expect(page).toHaveURL(/#chat$/);
  await expect(page.getByRole('region', { name: 'Result' }).getByText('3,658.00')).toBeVisible();
});

test('a new user can watch the tour from the home page and the Studio', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Watch the 2-minute tour' }).click();
  const video = page.getByRole('dialog').locator('video');
  await expect(video).toHaveAttribute('src', '/tour/skillforge-tour.webm');
  await expect.poll(() => video.evaluate((v) => v.duration)).toBeGreaterThan(60);
  await page.keyboard.press('Escape');
  await page.goto('/#chat');
  await page.getByRole('button', { name: 'New here? Watch the 2-minute tour' }).click();
  await expect(page.getByRole('dialog').locator('video')).toBeVisible();
});
