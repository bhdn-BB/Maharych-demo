# Maharych

Українською: [що реалізовано та як взаємодіють сервіси](README.uk.md).

Maharych is a web application for conducting AI-assisted interviews. Nginx serves a Next.js frontend and Go API through one local address. Python services handle the Gemini conversation and RabbitMQ-backed PDF export; services share a gRPC contract.

The current scope is defined in [specification v8](reports/technical-spec-v8.md): an adaptive oral interview in Ukrainian or English, five main questions with two follow-ups each, server-generated question speech, persistent feedback and PDF export. See the [launch and demo runbook](docs/development/demo-runbook.md) and [validation evidence](docs/development/adaptive-validation.md).

## Repository layout

```text
backend/
  src/                Go API, authentication, persistence, and WebSocket bridge
  tests/              Reserved for integration fixtures; unit tests live beside Go code
  docs/               Generated API reference
frontend/
  src/                Next.js application and UI
  tests/              Frontend hook and authentication tests
  docs/               Frontend documentation
voice_ai_service/
  src/                Python interview and voice processing service
  tests/              Dialogue, persistence, provider and transport tests
  docs/               Voice AI documentation
feedback_service/      RabbitMQ consumer and PDF report generator
proto/                 Shared Protocol Buffers definitions
deploy/                Nginx configurations and native Windows environment example
tools/                 Local startup, preflight and repository checks
docs/                  Architecture, development and validation instructions
reports/               Specifications and document generation sources
jrpc_labs456/          Coursework reports and historical evidence
.github/workflows/     Executable service checks
docker-compose.yml     Local multi-service setup
```

Each service keeps its own dependencies and build configuration. The Go API groups handlers, services, repositories, and models in `backend/src/internal/`; domain tests live beside their source. The Python service separates interfaces, repositories, services, and transport code in `voice_ai_service/src/voice_ai_service/app/`, with repository and stream tests in `voice_ai_service/tests/`.

## Run locally

1. Install Docker with Compose.
2. Copy the root `.env.example` to `.env` and set distinct random `JWT_SECRET` and `NEXTAUTH_SECRET` values (at least 32 characters). Google OAuth credentials are optional. Copy `voice_ai_service/.env.example` to `voice_ai_service/.env` and set `GEMINI_API_KEY`. The same key powers question generation, audio evaluation and Gemini TTS. Configure models with `GEMINI_MODEL` and `GEMINI_TTS_MODEL`; access and quotas must be checked with your project. Never overwrite an existing `.env`.
3. Start Docker Desktop. In PowerShell, run the following from the repository root:

   ```powershell
   cd D:\maharych-system
   docker compose up --build -d
   ```

   Check service status with `docker compose ps` and view logs with `docker compose logs -f`.
4. Open **http://localhost:8090**. Health: `http://localhost:8090/api/v1/health`; API docs: `http://localhost:8090/swagger/index.html`. Nginx routes `/api/auth/` to NextAuth and `/api/v1/` (including WebSocket) to Go. Application services and RabbitMQ remain internal; PostgreSQL binds to loopback for local tooling. A completed interview's result page offers a PDF download after the worker has generated it.

Google OAuth callback for this setup: `http://localhost:8090/api/auth/callback/google`. Use email/password without OAuth. Stop with `docker compose stop` to preserve data.

For Windows without Docker, follow the [native runbook](docs/development/native-runbook.md). It uses the same public address and a separate Nginx configuration with loopback upstreams.

For service-level development, use `frontend` with `pnpm install` and `pnpm dev`, `backend` with `make run` after copying `backend/.env.example` to `backend/.env`, or `voice_ai_service/src` with `uvicorn voice_ai_service.main:app --reload` after installing each service's dependencies and configuring its environment.

## Verification and contribution

See [validation commands and current results](docs/development/adaptive-validation.md), [contribution instructions](CONTRIBUTING.md), and the [repository structure](docs/development/repository-layout.md). Each service has its own README and dependencies; root Nx descriptors are optional metadata, not a required package installation.

Tests with provider substitutes do not prove a live microphone → Gemini → result → PDF flow. Check the validation record before claiming end-to-end readiness.

## Agent workflows

Repository instructions live in `AGENTS.md`, with backend-specific rules in `backend/AGENTS.md`. Shared Go/auth skills are stored once in `.agents/skills/`. See [development instructions](docs/development/agent-workflows.md) for their scope, source versions, and CI checks.
