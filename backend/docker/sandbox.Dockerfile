# The image skills run in when SkillForge itself runs in Docker (compose.prod.yaml). The sandbox's own code is
# baked in, because a container started through the host's Docker can't see files inside the worker container.
# Each skill gets a throwaway container from this image: no network, read-only, no capabilities, small limits.
FROM python:3.14-slim
COPY backend/app/sandbox/child.py backend/app/sandbox/policy.py backend/app/sandbox/tools.py /sandbox/
USER 65534:65534
WORKDIR /sandbox
