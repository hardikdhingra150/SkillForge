import js from '@eslint/js';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';

export default [
  { ignores: ['dist/', 'node_modules/', 'backend/', 'outputs/', 'work/', 'test-results/', 'playwright-report/'] },
  js.configs.recommended,
  {
    files: ['src/**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    settings: { react: { version: 'detect' } },
    plugins: { react, 'react-hooks': reactHooks },
    rules: {
      // Mark JSX usage so imported components are not reported as unused.
      'react/jsx-uses-vars': 'error',
      'react/jsx-uses-react': 'error',
      ...reactHooks.configs.recommended.rules,
      // Empty catch blocks guard optional storage access (private mode, blocked cookies).
      'no-empty': ['error', { allowEmptyCatch: true }],
      'no-unused-vars': ['error', { varsIgnorePattern: '^_', argsIgnorePattern: '^_', ignoreRestSiblings: true }],
    },
  },
  {
    files: ['src/**/*.test.{js,jsx}', 'src/test/**/*.js'],
    languageOptions: { globals: globals.node },
  },
  {
    // Playwright specs run in Node but pass callbacks that run in the page.
    files: ['e2e/**/*.js'],
    languageOptions: { ecmaVersion: 'latest', sourceType: 'module', globals: { ...globals.node, ...globals.browser } },
  },
  {
    files: ['*.config.js'],
    languageOptions: { globals: globals.node },
  },
];
