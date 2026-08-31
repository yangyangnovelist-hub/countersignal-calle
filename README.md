# CounterSignal

[![CI](https://github.com/yangyangnovelist-hub/countersignal-calle/actions/workflows/ci.yml/badge.svg)](https://github.com/yangyangnovelist-hub/countersignal-calle/actions/workflows/ci.yml)

**Customer discovery that is allowed to tell the founder they are wrong.** CounterSignal freezes
the segment, hypothesis, five questions, and an 8/5/3 decision rule before CALL-E contacts one
authorized participant. Consent-bound contradictions are load-bearing; voicemail and ambiguous
answers never pad the denominator.

[Open the judge console](https://countersignal.vercel.app/) ·
[Inspect the published evidence](https://yangyangnovelist-hub.github.io/countersignal-calle/) ·
[Review the merged CALL-E contribution](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/198) ·
[Inspect the zero-call preview](artifacts/example-preview.json) ·
[Inspect the deterministic contradiction](artifacts/example-simulation.json) ·
[Run the verification suite](TESTING.md)

## What a judge can verify

1. Open the judge console and click **Contradiction** three times. The frozen rule changes the
   experiment from `collecting` to `hypothesis_weakened`; no phone call is created.
2. Inspect `artifacts/example-preview.json`: the exact CALL-E task, strict output schema, masked
   destination, protocol hash, and idempotency key are visible before dispatch.
3. Run `uv run pytest --cov=src/countersignal`. The suite imports `calle-ai==0.2.0`, sends a real
   SDK `POST /v1/calls` to a loopback capture server, observes the poll, and verifies the bound
   result. Tests never place an external phone call.
4. Run the loopback operator console with `uv run countersignal-web`. Live calls are disabled by
   default.

## Decisive proof sequence

```text
freeze segment + hypothesis + five questions + 8/5/3 rule
  → authorize one participant and exact destination
  → CALL-E discloses AI and asks the frozen questions without pitching
  → strict structured result + recipient-side evidence
  → bind call, destination, experiment, and protocol hash
  → confirmation / contradiction / unknown
  → apply the frozen rule; unknown never enters the denominator
```

The decisive mechanism is not high-volume calling. It is **pre-registration plus evidence-bound
contradiction**: the protocol cannot be quietly rewritten after responses arrive.

## Why CALL-E is load-bearing

CALL-E performs the phone interview, AI disclosure, fixed-question sequence, and structured result
generation at runtime. CounterSignal supplies the non-leading task, strict schema, protocol hash,
idempotency reservation, recipient-evidence corroboration, and deterministic decision boundary.
Without the phone execution there is no participant evidence to classify.

## Run locally

Requires Python 3.12 and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev

# Exact task and masked destination; creates no call
uv run countersignal --request examples/example.json

# Deterministic no-call proof routes
uv run countersignal --request examples/example.json --simulate confirmation
uv run countersignal --request examples/example.json --simulate contradiction
uv run countersignal --request examples/example.json --simulate ambiguous
uv run countersignal --request examples/example.json --simulate voicemail

# Browser operator surface; live execution remains disabled
uv run countersignal-web
```

Then open `http://127.0.0.1:8767/`.

## Live execution boundary

Only call a number you own or a consenting adult has explicitly authorized. Live mode requires all
of the following: server-side `CALLE_API_KEY`, `CALLE_LIVE_CALLS_ENABLED=true`, exact E.164
allowlisting, recipient authorization confirmation, frozen-protocol confirmation, and a fresh
durable idempotency reservation.

The one-shot synthetic validation protocol is documented in
[`LIVE-VALIDATION.md`](LIVE-VALIDATION.md). Failed or ambiguous outcomes stay local and are not
blindly redialed.

## Trust model and limitations

- The task discloses that the caller is AI and ends before research questions if consent is absent.
- The five questions are sent verbatim; the task prohibits pitching, coaching, leading follow-ups,
  names, contact details, credentials, payment data, and contract terms.
- A confirmation or contradiction counts only when the terminal result, call ID, experiment,
  protocol hash, exact destination, evidence list, and recipient quote corroborate.
- Unknown, voicemail, low-confidence, malformed, unbound, or uncorroborated results do not count.
- The output is an operational research signal. It is not a representative sample, causal result,
  population estimate, or product-market-fit certification.

See [`THREAT_MODEL.md`](THREAT_MODEL.md) for the explicit failure boundaries.

## Verification status

- 61 automated tests pass with 91.26% coverage.
- Ruff passes with no findings.
- CI validates HTML semantics and audits the locked runtime dependency graph for known vulnerabilities.
- Desktop and mobile browser flows have been exercised with headless Chromium.
- The published CALL-E SDK is invoked at runtime in the HTTP integration test.
- The implementation is merged into CALL-E's official phone-agent repository through
  [PR #198](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/198).
- A public real-provider result is not claimed until the consented live protocol succeeds.

## What was built during the event

The frozen experiment model, CALL-E task and schema, runtime adapter, durable reservation,
evidence-binding policy, 8/5/3 decision engine, CLI, operator console, published evidence console,
live-validation runner, and complete verification suite were built during the event.

CounterSignal reuses the official CALL-E Python SDK and reliability patterns from the author's
MIT-licensed IncidentBridge entry. The research model, schema, routing, decision mechanism, user
experience, and evidence contract are independent. See [`THIRD_PARTY.md`](THIRD_PARTY.md).

MIT licensed.
