# Maharych

[![backend](https://github.com/bhdn-BB/Maharych-demo/actions/workflows/backend.yml/badge.svg)](https://github.com/bhdn-BB/Maharych-demo/actions/workflows/backend.yml)
[![feedback-service](https://github.com/bhdn-BB/Maharych-demo/actions/workflows/feedback-service.yml/badge.svg)](https://github.com/bhdn-BB/Maharych-demo/actions/workflows/feedback-service.yml)
[![voice-ai-service](https://github.com/bhdn-BB/Maharych-demo/actions/workflows/voice-ai-service.yml/badge.svg)](https://github.com/bhdn-BB/Maharych-demo/actions/workflows/voice-ai-service.yml)
[![nginx](https://github.com/bhdn-BB/Maharych-demo/actions/workflows/nginx.yml/badge.svg)](https://github.com/bhdn-BB/Maharych-demo/actions/workflows/nginx.yml)

Maharych is a web application for practising IT job interviews by voice. A candidate fills in a profile, picks a role, level, track and language, answers questions out loud and gets a transcript, scores and recommendations. Finished interviews stay in the history, and a background worker turns each result into a PDF report.

## How it works

```text
browser ──► nginx :8090 ──► frontend (Next.js)      pages, NextAuth
                       └──► backend (Go, Gin)       REST API, JWT, WebSocket audio
                                  │ gRPC
                                  ▼
                            voice_ai (Python)       adaptive dialogue, Gemini, TTS, scoring
                                  │ outbox → RabbitMQ
                                  ▼
                            feedback_worker         PDF report → PostgreSQL
```

- **Interview flow:** five main questions with up to two follow-ups each, in Ukrainian or English. Question speech is generated on the server; the candidate's answers are streamed as audio over WebSocket.
- **Results:** transcript, per-question scores, strengths and recommendations, plus a downloadable PDF once the worker has rendered it.
- **Accounts:** email/password or Google sign-in; admins are listed in `ADMIN_EMAILS`.

## Repository layout

```text
frontend/              Next.js + React + TypeScript UI (src/app routes, components, api clients, hooks)
backend/               Go API: src/cmd/server entry point, src/internal domain modules, docs/ Swagger
voice_ai_service/      Python FastAPI + gRPC service: dialogue, Gemini, TTS, evaluation, outbox relay
feedback_service/      RabbitMQ consumer that renders and stores PDF reports (ReportLab)
proto/                 Shared Protocol Buffers contract and client generator
deploy/nginx/          Gateway configuration for Docker Compose
tests/system/          End-to-end API checks against a running stack
.github/workflows/     CI: build and test per service, nginx config check
docker-compose.yml     Full local stack
```

Each service owns its dependencies, Dockerfile and README. The Go API follows `handler → service → repository` inside `backend/src/internal/<module>`, with unit tests next to the code. The Python service separates interfaces, repositories, services and transport in `voice_ai_service/src/voice_ai_service/app/`.

## Run locally

1. Install Docker with Compose.
2. Copy `.env.example` to `.env` and set `POSTGRES_PASSWORD`, `RABBITMQ_PASSWORD` and two different random values for `JWT_SECRET` and `NEXTAUTH_SECRET` (at least 32 characters). Google OAuth is optional.
3. Copy `voice_ai_service/.env.example` to `voice_ai_service/.env` and set `GEMINI_API_KEY`; models are chosen with `GEMINI_MODEL` and `GEMINI_TTS_MODEL`.
4. From the repository root:

   ```sh
   docker compose up --build -d
   docker compose ps
   ```

5. Open **http://localhost:8090**. Health check: `/api/v1/health`, API reference: `/swagger/index.html`.

For Google sign-in, register `http://localhost:8090/api/auth/callback/google` as the redirect URI. Stop the stack with `docker compose stop` to keep the data.

### Working on one service

| Service | Setup | Run | Test |
| --- | --- | --- | --- |
| frontend | `pnpm install` | `pnpm dev` | `pnpm test` |
| backend | copy `backend/.env.example` to `backend/.env` | `make run` | `go test ./...` |
| voice_ai_service | `pip install -r requirements-dev.txt` | `uvicorn voice_ai_service.main:app --reload` (from `src/`) | `PYTHONPATH=src python -m unittest discover -s tests` |
| feedback_service | `pip install -r requirements.txt` | `python worker.py` | `python -m unittest test_worker -v` |

Unit tests use provider substitutes, so they do not exercise a live microphone → Gemini → PDF run; check that flow manually in the running stack.

## Contributing

Work happens on short-lived branches and lands in `master` through pull requests with review and green CI. See [CONTRIBUTING.md](CONTRIBUTING.md).
