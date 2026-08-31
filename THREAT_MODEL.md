# Threat model

| Failure | Control | Safe result |
|---|---|---|
| Founder rewrites the questions after seeing answers | Canonical frozen protocol hash is bound into CALL-E metadata | Result becomes `unknown` |
| Interview turns into a pitch | Exact task prohibits disclosure, persuasion, coaching and extra leading questions | Call remains bounded; transcript is reviewable |
| Participant did not consent or match the segment | Explicit structured consent and segment fields | Evidence does not count |
| Voicemail or ambiguous answer inflates support | Only corroborated confirmation/contradiction counts | Denominator is unchanged |
| Model invents a supporting quote | Quote tokens must occur in recipient-side transcript evidence | Result becomes `unknown` |
| Wrong call, destination or experiment is replayed | Bind call ID, destination, experiment ID and protocol hash | Result becomes `unknown` |
| Duplicate or uncertain dispatch | SQLite reservation is written before provider dispatch | Retry is blocked for reconciliation |
| Research output is overclaimed | Every route carries an explicit non-PMF claim boundary | Output remains an operational signal |

CounterSignal is not a survey sampling system, dialer campaign, sales agent, or product-market-fit
oracle. Live execution is intentionally loopback-operated and exact-destination allowlisted.
