#!/bin/sh
# One container, three processes (Hugging Face Spaces and similar hosts): the local model, the worker and the API.
# The model and the worker restart by themselves if they stop; the API is the container's main process.
set -e

# The owner's Codex login, from the CODEX_AUTH_JSON secret (the contents of ~/.codex/auth.json).
if [ -n "$CODEX_AUTH_JSON" ]; then
  mkdir -p "$CODEX_HOME" && printf '%s' "$CODEX_AUTH_JSON" > "$CODEX_HOME/auth.json" && chmod 600 "$CODEX_HOME/auth.json"
fi

(while true; do ollama serve >/tmp/ollama.log 2>&1; sleep 3; done) &

alembic upgrade head
python -m app.register_builtin_skills

(while true; do python -m app.worker; echo "Worker stopped; restarting in 5 seconds." >&2; sleep 5; done) &

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-7860}" --proxy-headers
