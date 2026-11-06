# SkillForge API and worker. Built by compose.yaml; the same image runs both.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# The Docker CLI, so skills can run in throwaway containers (SANDBOX_BACKEND=docker, compose.prod.yaml).
COPY --from=docker:27-cli /usr/local/bin/docker /usr/local/bin/docker

# Optional: the Claude Code and Codex CLIs, for the site owner's own chats (compose.prod.yaml turns this on).
ARG INSTALL_AGENT_CLIS=false
RUN if [ "$INSTALL_AGENT_CLIS" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends nodejs npm ca-certificates \
      && npm install -g --no-fund --no-audit @anthropic-ai/claude-code @openai/codex \
      && npm cache clean --force && rm -rf /var/lib/apt/lists/*; \
    fi

COPY backend/ ./
COPY demo_data/ /app/demo_data/

RUN useradd --create-home --uid 10001 skillforge && chown -R skillforge /app
USER skillforge

EXPOSE 8000
CMD ["sh", "docker/start-api.sh"]
