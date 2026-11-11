# Contributing

Read [AGENTS.md](AGENTS.md) and the affected service README. Keep changes within the agreed interview scope in [the module audit](docs/development/module-functional-audit.md). Services own their dependencies; shared transport changes start in `proto/`.

Use a branch and a pull request. Run [the checks for affected services](docs/development/validation.md). Regenerate Swagger when public API annotations change, and Go/Python clients together when protobuf changes. Record what actually ran, including skipped tests and external dependencies.

Before staging:

```sh
python tools/check_repository.py
git status --short
git diff --check
git diff --cached --check
```

Stage intended paths explicitly, then inspect `git diff --cached --stat` and `git diff --cached`. Existing staged changes belong to their author; do not reset them. Commit only after this review. No repository script commits or pushes automatically.

Keep `.env` files, API keys, virtual environments, `node_modules`, binaries, logs and runtime artifacts local. Commit `.env.example` with placeholders. Coursework reports live separately in `jrpc_labs456/`; historical validation results do not describe a new run. Preserve third-party skill licenses and source attribution in `.agents/skills/`.
