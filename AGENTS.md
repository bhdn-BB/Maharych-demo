# Repository Guidelines

## Project Structure

Maharych is a multi-service AI interview application. Each service owns its dependencies and build commands; consult its README for current setup.

- `backend/`: Go API, authentication, persistence, and WebSocket/gRPC gateway; tests live beside source in `src/internal/`.
- `frontend/`: Next.js UI, NextAuth session, and API clients; source is in `src/` and tests in `tests/`.
- `voice_ai_service/`: Python conversation and feedback logic, with tests in `tests/`.
- `feedback_service/`: RabbitMQ PDF worker and its tests.
- `proto/` holds shared contracts; `deploy/`, `tools/`, `docs/`, and `reports/` contain deployment configuration, utilities, documentation, and specifications.

## Build, Test, and Development

Run commands from the named directory:

- Root: `docker compose config --quiet` checks configuration; `docker compose up --build -d` builds and starts the stack at `http://localhost:8090`.
- `backend/`: `make run`, `make build`, and `make test` run, build, and test the API. `make swagger` regenerates API documentation.
- `frontend/`: `pnpm install`, `pnpm dev`, `pnpm build`, `pnpm lint`, `pnpm typecheck`, and `pnpm test` install, run, build, and check the UI.
- `voice_ai_service/`: install `requirements-dev.txt`, then run `PYTHONPATH=src python -m unittest discover -s tests` (set `PYTHONPATH` using your shell's syntax).
- `feedback_service/`: `python -m unittest discover -s . -p 'test_*.py' -v` runs worker tests.

## Style and Testing

Follow `.editorconfig`: UTF-8, LF, two-space indentation by default, four spaces for Python, and tabs for Go and Makefiles. Format Go with `gofmt`; frontend uses ESLint and Prettier (`pnpm format`). Follow existing names: Go `*_test.go`, Python `test_*.py`, and frontend `*.test.ts(x)`.

Validate affected services and contracts; report what ran and any skipped checks. Provider substitutes do not establish live end-to-end behavior. Regenerate Swagger after public annotation changes and both Go and Python clients after protobuf changes.

## Contributions and Configuration

Use a branch and pull request; describe the change, validation, and any skipped checks or dependencies. Recent commit subjects are short, lowercase descriptions, such as `add dashboard page`. Before staging, run `python tools/check_repository.py` and `git diff --check`; stage intended paths and inspect the staged diff. Preserve unrelated changes.

Copy `.env.example` files for local configuration; never commit secrets or overwrite an existing `.env`. See `CONTRIBUTING.md` and service READMEs for details.

## Agent Instructions

Read `backend/AGENTS.md` before changing the backend or auth integration. For Go/auth implementation, review, or verification, read the relevant `.agents/skills/golang-pro/SKILL.md` or `.agents/skills/auth-implementation-patterns/SKILL.md`; source attribution is in `docs/development/skill-sources.md`. Read only needed references and keep project instructions outside the skill packages. Repository behavior and the requested scope take precedence over generic guidance.

Consult `docs/development/module-functional-audit.md` before expanding or refactoring modules. Distinguish inspected code from tested behavior and stay within requested scope. Executable CI is in `.github/workflows/`; Markdown workflows are not automatic jobs.
