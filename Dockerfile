FROM python:3.9.6-slim

WORKDIR /code

# Install the application dependencies.
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-cache

# Copy the application into the container (adjusted to match your folder structure)
COPY ./app /code/app
COPY ./main.py /code/

# Create nonroot user
RUN groupadd -r nonroot && useradd -r -g nonroot nonroot \
    && mkdir -p /home/nonroot \
    && chown -R nonroot:nonroot /home/nonroot

USER nonroot

CMD ["/code/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
