import { useId, useState } from 'react';
import { LogIn, ShieldCheck, UserPlus } from 'lucide-react';

/** Sign in or create an account (servers running with AUTH_MODE=accounts). */
export function AuthScreen({ auth }) {
  const uid = useId();
  const [mode, setMode] = useState('signin');
  const [form, setForm] = useState({ email: '', password: '', name: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const creating = mode === 'signup';
  const field = (name) => ({
    id: `${uid}-${name}`,
    value: form[name],
    disabled: busy,
    onChange: (event) => setForm({ ...form, [name]: event.target.value }),
  });

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      if (creating) await auth.signUp(form.email, form.password, form.name);
      else await auth.signIn(form.email, form.password);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="auth-screen" aria-labelledby={`${uid}-title`}>
      <div className="auth-card">
        <p className="auth-eyebrow"><ShieldCheck size={13} />YOUR WORKSPACE</p>
        <h1 id={`${uid}-title`}>{creating ? 'Create your account' : 'Sign in to SkillForge'}</h1>
        <p className="auth-lead">
          Your tasks, chats and history are private to you. Skills are shared, so everyone
          benefits when one is built or repaired.
        </p>

        {auth.allowSignup && (
          <div className="auth-tabs" role="tablist" aria-label="Account">
            <button type="button" role="tab" aria-selected={!creating} onClick={() => { setMode('signin'); setError(''); }}>Sign in</button>
            <button type="button" role="tab" aria-selected={creating} onClick={() => { setMode('signup'); setError(''); }}>Create account</button>
          </div>
        )}

        <form onSubmit={submit} className="auth-form">
          {creating && (
            <label htmlFor={`${uid}-name`}>Name <span>(optional)</span>
              <input {...field('name')} autoComplete="name" maxLength={120} />
            </label>
          )}
          <label htmlFor={`${uid}-email`}>Email
            <input {...field('email')} type="email" autoComplete="email" required maxLength={254} />
          </label>
          <label htmlFor={`${uid}-password`}>Password
            <input {...field('password')} type="password" required minLength={creating ? 10 : 1} maxLength={200}
              autoComplete={creating ? 'new-password' : 'current-password'} />
          </label>
          {creating && <p className="auth-hint">At least 10 characters.</p>}
          {error && <p role="alert" className="auth-error">{error}</p>}
          <button type="submit" className="auth-submit" disabled={busy}>
            {creating ? <UserPlus size={15} /> : <LogIn size={15} />}
            {busy ? 'One moment…' : creating ? 'Create account' : 'Sign in'}
          </button>
        </form>
        {!auth.allowSignup && <p className="auth-hint">New accounts are closed on this server. Ask its owner for access.</p>}
      </div>
    </section>
  );
}
