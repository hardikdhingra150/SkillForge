import { useId, useState } from 'react';

import { getApiToken, setApiToken } from '../api/skillforgeProcess.js';

// Paste the server's API_TOKEN once; it is stored in this browser and sent with every request.
export function ApiTokenForm() {
  const id = useId();
  const [saved, setSaved] = useState(() => Boolean(getApiToken()));
  const [draft, setDraft] = useState('');

  const save = (event) => {
    event.preventDefault();
    setApiToken(draft.trim());
    setSaved(Boolean(draft.trim()));
    setDraft('');
  };

  const clear = () => {
    setApiToken('');
    setSaved(false);
  };

  return (
    <form className="api-token" onSubmit={save}>
      <label htmlFor={id}>
        API access token
        <small>{saved ? 'Saved in this browser' : 'Needed when the API sets API_TOKEN'}</small>
      </label>
      <div>
        <input
          id={id}
          type="password"
          autoComplete="off"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={saved ? '••••••••' : 'Paste API_TOKEN'}
        />
        <button type="submit" disabled={!draft.trim()}>Save</button>
        {saved && <button type="button" onClick={clear}>Forget</button>}
      </div>
    </form>
  );
}
