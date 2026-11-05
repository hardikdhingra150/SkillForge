import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

import { mockApi } from './mockApi.js';

const pages = ['/', '/#workbench', '/#chat', '/#library', '/#models', '/#review', '/#console', '/#activity', '/#governance'];

for (const theme of ['dark', 'light']) {
  test(`no WCAG 2 AA violations in ${theme} mode`, async ({ page }) => {
    await page.addInitScript((value) => localStorage.setItem('skillforge-theme', value), theme);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await mockApi(page);

    const found = [];
    for (const path of pages) {
      await page.goto(path);
      await page.waitForTimeout(800);
      const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
      for (const violation of violations) {
        found.push(`${path} ${violation.id}: ${violation.nodes.map((node) => node.target.join(' ')).join(', ')}`);
      }
    }
    expect(found).toEqual([]);
  });
}

test('the workspace can be navigated with the keyboard', async ({ page }) => {
  await mockApi(page);
  await page.goto('/#workbench');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'SkillForge home' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Workbench' }).first()).toBeFocused();
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/#chat$/);
});
