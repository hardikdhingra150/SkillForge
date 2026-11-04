import { defineConfig, devices } from '@playwright/test';

// Smoke tests run the real frontend against a mocked API (see e2e/mockApi.js), so CI needs no backend.
export default defineConfig({
  testDir: 'e2e',
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://127.0.0.1:5180',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npx vite --host 127.0.0.1 --port 5180 --strictPort',
    url: 'http://127.0.0.1:5180',
    reuseExistingServer: !process.env.CI,
    env: { VITE_API_BASE_URL: 'http://127.0.0.1:5999/api/v1' },
  },
});
