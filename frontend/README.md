# Frontend

The Maharych frontend is a Next.js application using React and TypeScript. Application code lives in `src/`, with route files in `src/app/`, feature components in `src/components/pages/`, and API clients in `src/api/`.

From this directory, run `pnpm install` and `pnpm dev` to start the development server at `http://localhost:3000`. Server-side NextAuth calls use `BACKEND_URL` (the internal backend address in Compose); browser calls use `NEXT_PUBLIC_BACKEND_URL`. Authentication endpoints are implemented directly in the Go backend auth module. Google OAuth requires `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in the frontend environment and the same client ID in the Go backend. Set `NEXT_PUBLIC_BACKEND_URL` to the public Go API URL when it differs from `http://localhost:8080`.

Component and hook tests live in `tests/`. The `docs/` directory is reserved for frontend-specific notes.

The setup screen selects a role, level, one of two oral interview modes and Ukrainian or English. Algorithms covers spoken solutions, data structures, time and space complexity. System design adapts to the candidate's CV and specialization and covers service choices, budget and architectural tradeoffs. New sessions use adaptive dialogue (scenarioVersion 2) without selecting a task. Questions are displayed and spoken by the server; answers use complete WebM/Opus recordings, bounded to 180 seconds and 8 MiB. The interview screen supports speech replay, reconnect and retry of the pending answer with its original ID. The task catalog, behavioral mode and camera/screen-sharing controls are removed; the existing page layout and styling are retained.

See the [repository README](../README.md) for the full workspace layout and Docker Compose setup.
