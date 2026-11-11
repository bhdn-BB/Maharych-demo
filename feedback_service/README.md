# PDF feedback worker

Consumes the durable RabbitMQ queue `feedback.pdf` (exchange `maharych.events`, key `feedback.ready`; failures go to `feedback.pdf.retry` with a TTL, then to `feedback.pdf.dlq` after `PDF_MAX_ATTEMPTS`), reads committed interview feedback from PostgreSQL, renders a Unicode PDF with ReportLab and stores it in `feedback_reports`. Repeated delivery does not create another saved report.

Start the full stack from the repository root with `docker compose up --build -d`. Compose starts the worker after AI migrations and health checks. The worker has no HTTP API or published port.

For native Windows development, use `tools/local.ps1 -Action Worker` after following the [native runbook](../docs/development/native-runbook.md). For a standalone process, install `requirements.txt`, export `DATABASE_URL` and `RABBITMQ_URL`, then run `python worker.py`. The `.env.example` is a reference; the worker does not load it automatically. Set `PDF_FONT_PATH` to an installed Unicode TTF font outside the Linux image.

Run unit tests from this directory:

```sh
python -m unittest discover -s . -p 'test_*.py' -v
```

Tests cover PDF output, duplicate delivery and invalid events using database substitutes. Actual queue delivery and database persistence require the integration harness described in [validation instructions](../docs/development/validation.md).
