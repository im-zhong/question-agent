# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Monorepo Structure

```
question-agent-v1/
├── question_agent/    # Python backend (FastAPI)
├── frontend/          # Vite + TanStack Router (React + TypeScript + Tailwind + shadcn/ui)
├── tests/             # Python tests
├── docs/              # Pre-dev documentation
└── .harness/          # Toolchain config
```

## Commands

### Backend (Python)

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

### Frontend (Vite + TanStack Router)

```bash
# Dev server (from frontend/ directory)
cd frontend && npm run dev

# Type check
cd frontend && npx tsc -b

# Build
cd frontend && npm run build

# Preview production build
cd frontend && npm run preview
```

### Full Development

```bash
# Start both servers (two terminals)
# Terminal 1: Backend
uv run question-agent
# Terminal 2: Frontend
cd frontend && npm run dev
```

Frontend runs at `http://localhost:5173` (Vite default), backend at `http://localhost:8000`.
Frontend connects to backend via Vite dev proxy (`/api` → `http://localhost:8000`).
Production: set `VITE_API_URL` env var for build-time API URL configuration.

## Code Style

### Python
- Line length: 100 (ruff). Python 3.12+.
- ruff selects: E, F, I, N, W, UP. Import sorting configured with `known-first-party = ["question_agent"]`.
- mypy runs in **strict mode** — every function and method must be fully type-annotated.

### TypeScript / React
- Indent: 2 spaces. Single quotes. Semicolons.
- Components use named exports, not default exports (shadcn/ui convention).
- Routing: TanStack Router file-based routing. Routes in `frontend/src/routes/`.
- Auto-generated route tree at `frontend/src/routeTree.gen.ts` — do not edit manually.

## Testing

- Unit tests use in-process ASGI transport (no running server needed). Integration tests in `tests/integration/` require a running server at `http://localhost:8000`.
- pytest `asyncio_mode = "auto"` — async test functions don't need decorators.
- Run a single test: `uv run pytest -k 'test_name'`.

## Architecture

- Backend: No `src/` layout — the package is at `question_agent/`. Config via pydantic-settings in `question_agent/config.py`, reads `.env` for `GLM_API_KEY` and `GLM_MODEL`. See `.env.example`.
- Frontend: Vite SPA with `src/` layout. Routes in `frontend/src/routes/`. Components in `frontend/src/components/`.
- Structured pre-dev workflow lives in `.claude/skills/`. Specs and roadmaps in `docs/superpowers/`.
