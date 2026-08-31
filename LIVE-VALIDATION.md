# Consented live interview validation

Use this only with a number you own or a consenting adult has explicitly authorized. The recipient
should know that CALL-E will identify itself as an AI research assistant and should answer the
interview honestly. Confirmation and contradiction are equally publishable when they pass the same
consent, segment, grounding and result-binding checks. Do not coach either answer.

```bash
export CALLE_API_KEY="<CALL_E_API_KEY>"
export CALLE_LIVE_CALLS_ENABLED="true"

uv run countersignal-consented-live-demo \
  --phone +<AUTHORIZED_E164_NUMBER> \
  --confirm-consent "I HAVE EXPLICIT CONSENT" \
  --confirm-frozen-protocol "THE PROTOCOL IS FROZEN"
```

At most one call is reserved. Any countable confirmation or contradiction creates
`artifacts/consented-live-interview.json` without publishing the phone number, participant
identity, transcript, recording, or verbatim quote. Ambiguous, non-response, wrong-segment or
otherwise uncountable outcomes are written only to
`data/consented-live-last-result.json`; inspect it and do not blindly retry.

The publish rule is fixed before dispatch. The runner cannot hide a countable confirmation while
publishing only a preferred contradiction (or vice versa). One completed interview remains
directional evidence, not a representative sample or product-market-fit claim.
