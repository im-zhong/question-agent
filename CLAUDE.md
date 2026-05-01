# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# All checks (lint + format check + type check + tests)
uv run ruff check . && uv run ruff format --check . && uv run mypy question_agent/ && uv run pytest

# Dev server
uv run question-agent

# Integration tests only (requires running server)
uv run pytest tests/integration/ -v

# Unit tests only (no server needed)
uv run pytest --ignore=tests/integration/ -v
```

Always use `uv run <tool>` — ruff, mypy, and pytest are dev dependencies, not globally installed.

## Code Style

- Line length: 100 (ruff). Python 3.12+.
- ruff selects: E, F, I, N, W, UP. Import sorting configured with `known-first-party = ["question_agent"]`.
- mypy runs in **strict mode** — every function and method must be fully type-annotated.

## Testing

- Unit tests use in-process ASGI transport (no running server needed). Integration tests in `tests/integration/` require a running server at `http://localhost:8000`.
- pytest `asyncio_mode = "auto"` — async test functions don't need decorators.
- Run a single test: `uv run pytest -k 'test_name'`.

## Architecture

- No `src/` layout — the package is at `question_agent/`.
- Config via pydantic-settings in `question_agent/config.py`, reads `.env` for `GLM_API_KEY` and `GLM_MODEL`. See `.env.example`.
- zai-sdk (GLM-5) is declared but not yet wired into application code.
- Structured pre-dev workflow lives in `.claude/skills/`. Specs and roadmaps in `docs/superpowers/`.
