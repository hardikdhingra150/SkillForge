# SkillForge API and worker. Built by compose.yaml; the same image runs both.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY demo_data/ /app/demo_data/

RUN useradd --create-home --uid 10001 skillforge && chown -R skillforge /app
USER skillforge

EXPOSE 8000
CMD ["sh", "docker/start-api.sh"]
