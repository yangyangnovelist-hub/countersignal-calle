# Consented live contradiction validation

Use this only with a number you own or a consenting adult has explicitly authorized. The recipient
should know that CALL-E will identify itself as an AI research assistant and should answer the
synthetic interview honestly. A contradiction is expected only when the recipient genuinely says
that an expeditor already handles every permit-status call; do not coach a false answer.

```bash
export CALLE_API_KEY="<CALL_E_API_KEY>"
export CALLE_LIVE_CALLS_ENABLED="true"

uv run countersignal-consented-live-demo \
  --phone +<AUTHORIZED_E164_NUMBER> \
  --confirm-consent "I HAVE EXPLICIT CONSENT" \
  --confirm-frozen-protocol "THE PROTOCOL IS FROZEN"
```

At most one call is reserved. A successful contradiction creates
`artifacts/consented-live-contradiction.json` without publishing the phone number, participant
identity, transcript, or recording. Any other outcome is written only to
`data/consented-live-last-result.json`; inspect it and do not blindly retry.
