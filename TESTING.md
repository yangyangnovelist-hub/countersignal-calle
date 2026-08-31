# Testing

Install and run the complete safe verification suite:

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest --cov=src/countersignal --cov-report=term-missing --cov-fail-under=90
```

The SDK integration test starts a loopback HTTP server, imports the published `calle-ai==0.2.0`
package, observes `POST /v1/calls`, bearer authentication, the CounterSignal idempotency key,
strict schema and metadata, and then observes `GET /v1/calls/{id}`. It proves runtime integration
without contacting an external phone number.

Critical regressions cover protocol mutation, duplicate dispatch, missing consent, unsupported
destinations, low confidence, malformed schema, wrong call ID, wrong protocol hash, missing
recipient transcript, uncorroborated quotes, ambiguous evidence, and voicemail.
