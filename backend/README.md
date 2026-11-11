# Backend

The Go API source is in `src/`. Entry points are in `src/cmd/`; domain handlers, services, repositories, models, and generated gRPC code are in `src/internal/`.

Authentication is implemented in `src/internal/auth/` within this API process. It handles `/api/v1/auth/register`, `/login`, and `/google` directly, owns users-table migrations, hashes/verifies passwords, validates Google ID tokens, and issues JWTs. REST/WebSocket handlers validate those JWTs and interview ownership. NextAuth in Next.js handles Google OAuth and the web session. Configure `JWT_SECRET` and the same `GOOGLE_CLIENT_ID` as the frontend; no Google client secret is needed in Go. Existing users and JWT claims are preserved. See [service boundaries](../docs/architecture/service-boundaries.md).

Copy `.env.example` to `.env`, then run `make run` from this directory after configuring the environment variables used by `src/internal/config/`. Run `make build` to build the API binary. API reference files are in `docs/`.

Go service tests live beside the code they exercise. The separate `tests/` directory is reserved for broader integration tests.

The candidate profile module exposes authenticated `GET /api/v1/profile` and `PUT /api/v1/profile`. It stores one profile per user through a repository interface and validates profile data in the service layer. Starting an interview requires a profile and valid seeded options. The audio gateway reads these records and sends startup context to the AI stream before forwarding audio.

New interviews use adaptive scenarioVersion 2, with role, level, `algorithms` or `system-design` focus and `uk`/`en` language. Algorithms is an oral coding interview about algorithms and time/space complexity; system design uses the candidate's CV, specialization and service/budget tradeoffs. New task-based starts are rejected. The task catalog routes are no longer registered. Existing persisted interviews and their task snapshots remain readable; no historical records are deleted. The options endpoint filters retired modes even when an existing database still contains them.

Completed AI feedback is available through authenticated `GET /api/v1/interviews/{id}/feedback`. The handler checks interview ownership before its repository calls the internal AI HTTP endpoint. Set `AI_SERVICE_HTTP_URL` to the private AI service address (`http://voice_ai:8000` in Docker Compose); it defaults to `http://localhost:8000` for local development.

`GET /api/v1/interviews/{id}/report.pdf` applies the same ownership check and returns the PDF after the RabbitMQ feedback worker has generated it. It returns 404 while the report is pending.

Authenticated `GET /api/v1/interviews?page=1&pageSize=10` returns the current user's paginated interview history.
