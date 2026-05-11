# Frontend — Vite + TanStack Router

## Key conventions
- File-based routing via TanStack Router. Routes live in `src/routes/`.
- `src/routeTree.gen.ts` is auto-generated — never edit manually.
- Route files export `Route` using `createFileRoute()` or `createRootRoute()`.
- Use `@tanstack/react-router` Link, useRouter, useNavigate, useParams — not Next.js APIs.
- Environment variables use `VITE_*` prefix (not `NEXT_PUBLIC_*`).
- API calls go through `/api` prefix (Vite dev proxy → FastAPI backend).
