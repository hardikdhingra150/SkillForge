# SkillForge's backend as one Hugging Face Space (Docker, free "CPU basic": 2 vCPU, 16 GB RAM).
# The API, the worker and a local model (Ollama, for visitors' chat) run in this one container, against your
# Supabase database. The frontend runs on Vercel. See DEPLOY.md.
#
# This file and README.md are all the Space holds: the build fetches SkillForge from GitHub. To deploy a newer
# version, use the Space's "Factory rebuild". SKILLFORGE_REF picks a branch or tag.

FROM alpine/git:2.47.2 AS source
ARG SKILLFORGE_REPO=https://github.com/hardikdhingra150/SkillForge.git
ARG SKILLFORGE_REF=main
RUN git clone --depth 1 --branch "$SKILLFORGE_REF" "$SKILLFORGE_REPO" /src

# Ollama for CPUs only: its GPU libraries are 4.5 GB and a free Space has no GPU.
FROM ollama/ollama:0.12.6 AS ollama
ARG OLLAMA_MODEL=qwen2.5-coder:3b
ARG BAKE_MODEL=true
# Bake the visitors' model into the image (about 1.9 GB), so a restarted Space doesn't download it again.
RUN if [ "$BAKE_MODEL" = "true" ]; then (ollama serve >/dev/null 2>&1 &) && sleep 5 && ollama pull "$OLLAMA_MODEL"; \
    else mkdir -p /root/.ollama/models; fi

FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Node, for the Claude Code and Codex CLIs (only the owner can use them; see DEPLOY.md).
ARG INSTALL_AGENT_CLIS=true
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && if [ "$INSTALL_AGENT_CLIS" = "true" ]; then \
         apt-get install -y --no-install-recommends nodejs npm \
         && npm install -g --no-fund --no-audit @anthropic-ai/claude-code @openai/codex && npm cache clean --force; \
       fi \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ollama /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama /usr/lib/ollama/libggml-*.so /usr/lib/ollama/

# Hugging Face runs the container as user 1000.
RUN useradd --create-home --uid 1000 user
WORKDIR /home/user/app/backend
COPY --from=source /src/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=source --chown=user /src/backend/ ./
COPY --from=source --chown=user /src/demo_data/ /home/user/app/demo_data/
COPY --from=ollama --chown=user /root/.ollama/models /home/user/.ollama/models

USER user
ENV HOME=/home/user \
    APP_ENV=production \
    AUTH_MODE=browser \
    SANDBOX_BACKEND=process \
    ALLOW_PROCESS_SANDBOX=true \
    OLLAMA_URL=http://127.0.0.1:11434 \
    OLLAMA_MODELS=/home/user/.ollama/models \
    PUBLIC_PROVIDERS='["ollama"]' \
    CHAT_TURNS_PER_DAY=50 \
    CHAT_TURNS_PER_DAY_TOTAL=500 \
    FORWARDED_ALLOW_IPS=* \
    CODEX_HOME=/home/user/.codex \
    PORT=7860

EXPOSE 7860
CMD ["sh", "docker/start-space.sh"]
