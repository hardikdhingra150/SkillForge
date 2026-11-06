#!/bin/sh
# One container for the whole backend (Render, Hugging Face Spaces and similar hosts): the worker and the API,
# plus a local model when the image has Ollama. The worker and model restart by themselves if they stop; the
# API is the container's main process and listens on $PORT.
set -e

# The owner's Codex login, from the CODEX_AUTH_JSON secret (the contents of ~/.codex/auth.json).
if [ -n "$CODEX_AUTH_JSON" ]; then
  mkdir -p "${CODEX_HOME:=$HOME/.codex}" && printf '%s' "$CODEX_AUTH_JSON" > "$CODEX_HOME/auth.json"
  chmod 600 "$CODEX_HOME/auth.json"
fi

if command -v ollama >/dev/null 2>&1; then
  (while true; do ollama serve >/tmp/ollama.log 2>&1; sleep 3; done) &
fi

# The starter skills (quick when already registered) and the worker run in the background while the API comes up:
# these hosts restart everything each time they wake up, so the site should answer as soon as it can. The worker
# both retry until the API's migration has finished.
(sleep 20
 until python -m app.register_builtin_skills; do echo "Starter skills not registered yet; retrying." >&2; sleep 10; done
 while true; do python -m app.worker; echo "Worker stopped; restarting in 5 seconds." >&2; sleep 5; done) &

# Migrates the database, then serves the API, loading the app only once (app/serve.py).
exec python -m app.serve
