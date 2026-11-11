# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

`AGENTS.md` (root) and `backend/AGENTS.md` are the authoritative project instructions — read them first; backend work (especially auth) also requires `backend/AGENTS.md` and the skills under `.agents/skills/`. Consult `docs/development/module-functional-audit.md` before expanding or refactoring modules. Tests with provider substitutes do not prove the live microphone → Gemini → result → PDF flow; say so rather than claiming end-to-end readiness.

## Architecture

Maharych is an AI-assisted oral interview app (uk/en). Request flow:

Browser → Nginx (`:8090`) → Next.js (`/api/auth/*` NextAuth) or Go API (`/api/v1/*`, incl. WebSocket) → gRPC → Python `voice_ai_service` (dialogue, transcription, evaluation, Gemini TTS). PostgreSQL holds all state (one DB, `maharych`); RabbitMQ carries feedback events to `feedback_service`, which renders PDFs back into PostgreSQL.

Ownership boundaries that span files:
- **Go** (`backend/src/internal/`, Gin + GORM, handler → service → repository per domain, DI in `src/cmd/server/main.go`) owns users/auth (bcrypt, Google ID-token validation, JWT HS256), profiles, interview options, public interview status, and the WebSocket↔gRPC `audio/bridge.go`. Schema via GORM `AutoMigrate`.
- **Python** (`voice_ai_service/src/voice_ai_service/app/`: `routers`, `grpc`, `services`, `repositories`, `interfaces`) owns conversation state, question bank, and feedback outbox. Schema via **Alembic** (`app/alembic/versions`), not GORM. Adaptive state is DB-backed under a row lock; the in-process session dict is not authoritative.
- **Frontend** (`frontend/src/`) — NextAuth owns the browser Google OAuth flow/session; the backend verifies the same `GOOGLE_CLIENT_ID` audience. Audio/TTS handled by hooks (`use-audio-stream`, `use-question-audio`).
- **Interview contract (v2 adaptive):** 5 main questions + 2 follow-ups each (max 15 answers; sessions saved before this change keep 3 + 1); clients send `start_recording` then an `answer` JSON message followed by one WebM/Opus blob (≤120 s); each answer is idempotent via `answerId`/`questionId`. Details: `docs/architecture/` and `reports/technical-spec-v8.md`.
- `proto/ai_service/v1/ai_service.proto` is the shared gRPC contract. AI HTTP/gRPC ports stay private in Compose.

## Commands

Root (Docker): `docker compose config --quiet` (validate), `docker compose up --build -d` (run at http://localhost:8090; Swagger at `/swagger/index.html`). Copy `.env.example` → `.env` (never overwrite an existing one); `voice_ai_service/.env` needs `GEMINI_API_KEY`. Native Windows runbook: `docs/development/native-runbook.md`.

Backend (`backend/`, Go module `maharych-api`):
- `make run` / `make build` / `make test` / `make tidy`
- Single test: `go test ./src/internal/interview -run TestName`
- `make swagger` after changing swaggo `@` annotations (output in `docs/`, don't hand-edit)
- Runtime-change checks: `go vet ./...`, `go test ./...`, `go build ./src/cmd/server`

Frontend (`frontend/`, pnpm, Next 16, vitest): `pnpm dev`, `pnpm build`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm format`. Single test: `pnpm vitest run tests/auth.test.ts`.

Voice AI (`voice_ai_service/`): `pip install -r requirements-dev.txt`, then `PYTHONPATH=src python -m unittest discover -s tests` (PowerShell: `$env:PYTHONPATH="src"`). Single test: `PYTHONPATH=src python -m unittest tests.test_<module>.<Class>.<method>`. Dev server: `uvicorn voice_ai_service.main:app --reload` from `src`.

Feedback worker (`feedback_service/`): `python -m unittest discover -s . -p 'test_*.py' -v`.

Protobuf: after editing the `.proto`, regenerate both Go and Python clients with `python proto/generate.py` (works around Windows cmd AutoRun; needs `grpcio-tools` and `protoc-gen-go`/`protoc-gen-go-grpc`). `make proto` in `backend/` / `voice_ai_service/` are the per-service alternatives.

Before staging: `python tools/check_repository.py` and `git diff --check`. CI is in `.github/workflows/` (Markdown workflows under `.agents/workflows/` are not automatic jobs).

## Conventions

- `.editorconfig`: UTF-8, LF, 2 spaces (4 for Python, tabs for Go/Makefiles). `gofmt` for Go; ESLint + Prettier for frontend.
- Go tests live beside source (`*_test.go`); Python `test_*.py`; frontend `*.test.ts(x)` in `frontend/tests/`.
- Commit subjects: short, lowercase (`add dashboard page`). Use a branch + PR; report validation run and checks skipped. Preserve unrelated working-tree changes.
- Never log the WebSocket `?token=` query string; never expose password hashes or Google subjects.
