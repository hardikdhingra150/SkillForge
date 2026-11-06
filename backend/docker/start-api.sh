#!/bin/sh
# Container start for the API: bring the database schema up to date, register the starter skills, serve.
set -e
alembic upgrade head
python -m app.register_builtin_skills
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
