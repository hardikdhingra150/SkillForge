import { getApiToken, request, setApiToken } from './skillforgeProcess.js';

// Accounts (when the server runs with AUTH_MODE=accounts). The session token is stored like an API token.
const json = (body) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const getAuthConfig = (signal) => request('/auth/config', { signal });
export const getMe = (signal) => request('/auth/me', { signal });

export async function signIn(email, password) {
  const result = await request('/auth/login', json({ email, password }));
  setApiToken(result.token);
  return result.user;
}

export async function signUp(email, password, name) {
  const result = await request('/auth/signup', json({ email, password, name }));
  setApiToken(result.token);
  return result.user;
}

export async function signOut() {
  if (getApiToken().startsWith('sfs_')) {
    await request('/auth/logout', { method: 'POST' }).catch(() => null);
  }
  setApiToken('');
}
