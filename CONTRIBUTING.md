# Contributing

## Branches and pull requests

1. Branch off `master`. Name the branch after the task: `feature/<topic>`, `fix/<topic>`, `docs/<topic>`, `ci/<topic>`.
2. Keep commits small, one logical change each, in the form `type(scope): summary` — for example `feat(backend): add interview options` or `test(feedback): cover retry queue`.
3. Open a pull request into `master` and fill in the template.
4. Merge only after a teammate's review and green checks for the services you touched.

## Before you push

- Run the tests of every service you changed (see the table in the [README](README.md#working-on-one-service)).
- Regenerate Swagger (`make swagger` in `backend/`) when public API annotations change.
- Change `proto/` first and regenerate Go and Python clients together when the gRPC contract changes.
- Check what you are about to commit: `git status --short`, `git diff --cached`.

## Keep out of the repository

`.env` files and API keys, virtual environments, `node_modules`, compiled binaries, `__pycache__`, logs and runtime artifacts. Commit `.env.example` with placeholders instead.
