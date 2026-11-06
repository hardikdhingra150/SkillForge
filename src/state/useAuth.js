import { useCallback, useEffect, useState } from 'react';

import { getAuthConfig, getMe, signIn, signOut, signUp } from '../api/auth.js';
import { getApiToken } from '../api/skillforgeProcess.js';

// mode: 'unknown' (API not reached yet) | 'off' (no sign-in) | 'accounts'
export function useAuth({ onChange } = {}) {
  const [state, setState] = useState({ mode: 'unknown', allowSignup: false, user: null, ready: false });

  const refresh = useCallback(async () => {
    let config;
    try {
      config = await getAuthConfig();
    } catch {
      setState((previous) => ({ ...previous, ready: true }));
      return;
    }
    let user = null;
    if (config.mode === 'accounts' && getApiToken().startsWith('sfs_')) {
      user = await getMe().then((me) => me.user).catch(() => null);
    }
    setState({ mode: config.mode, allowSignup: config.allow_signup, user, ready: true });
  }, []);

  useEffect(() => {
    refresh();
    const again = () => refresh();
    window.addEventListener('focus', again);
    return () => window.removeEventListener('focus', again);
  }, [refresh]);

  const done = (user) => {
    setState((previous) => ({ ...previous, user }));
    onChange?.();
    return user;
  };

  return {
    ...state,
    needsSignIn: state.mode === 'accounts' && !state.user,
    refresh,
    signIn: async (email, password) => done(await signIn(email, password)),
    signUp: async (email, password, name) => done(await signUp(email, password, name)),
    signOut: async () => {
      await signOut();
      done(null);
    },
  };
}
