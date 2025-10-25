FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# still need curl for the ECS container health check!
RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic-dev curl

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="$PYTHONPATH:/code"

WORKDIR /code

# Download dependencies as a separate step to take advantage of Docker's caching
# Leverage a bind mount to pyproject.toml to avoid having to copy into this layer
# Leverage a cache mount to /root/.cache/uv to speed up subsequent builds
# For some reason this command complains if /tmp/README.md is not present, so mount that too
RUN --mount=type=bind,source=pyproject.toml,target=/tmp/pyproject.toml \
    --mount=type=bind,source=poetry.lock,target=/tmp/poetry.lock \
    --mount=type=bind,source=README.md,target=/tmp/README.md \
    --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r /tmp/pyproject.toml

COPY app app
COPY alembic alembic
COPY alembic.ini alembic.ini
COPY prestart.sh prestart.sh

EXPOSE 80

CMD ["./prestart.sh"]