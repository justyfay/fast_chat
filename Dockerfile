FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /fast_chat

COPY pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-install-project --no-dev

COPY . .

RUN uv sync --frozen --no-dev

RUN chmod a+x /fast_chat/scripts/*.sh

ENV PATH="/fast_chat/.venv/bin:$PATH"
