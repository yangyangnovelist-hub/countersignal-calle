# CounterSignal: reproduce the decision

CounterSignal freezes an interview protocol before an authorized CALL-E call, then treats a corroborated contradiction as evidence against the hypothesis. The published Python policy is the source of truth for the decision.

## The default rule, in order

1. Three or more countable contradictions produce `hypothesis_weakened`, regardless of supporting evidence.
2. With fewer than three contradictions, fewer than eight countable interviews produce `collecting`.
3. Once eight countable interviews have been reached, at least five confirmations produce `hypothesis_supported_under_rule`.
4. Otherwise the result is `inconclusive`.

Only confirmations and contradictions enter the completed count. Voicemail, ambiguity, refusal, unreliable output and uncorroborated quotes do not count.

The order matters. At exactly eight completed interviews, five confirmations necessarily leave three contradictions: the result is **weakened**, not supported. A supported eight-interview example is **six confirmations and two contradictions**.

| Confirmations | Contradictions | Unknown | Completed | Expected decision |
| ---: | ---: | ---: | ---: | --- |
| 0 | 0 | 0 | 0 | collecting |
| 6 | 2 | 0 | 8 | hypothesis_supported_under_rule |
| 6 | 2 | 1 | 8 | hypothesis_supported_under_rule |
| 6 | 3 | 1 | 9 | hypothesis_weakened |
| 5 | 3 | 0 | 8 | hypothesis_weakened |

See [`decision_from_counts`](../src/countersignal/policy.py). These are exact policy examples, not customer research results.

## Corrected recording sequence

Use the [repository-owned evidence console](https://yangyangnovelist-hub.github.io/countersignal-calle/) from a clean ledger. Keep the synthetic/no-call label visible.

- Show the frozen segment, hypothesis, five questions and thresholds.
- Add six simulated confirmations and two simulated contradictions. Show eight completed interviews and provisional support under the rule.
- Add one simulated voicemail. Show that completed remains eight.
- Add one more simulated contradiction. Show the existing six confirmations remain, completed becomes nine, and the decision changes to weakened.
- Open the zero-call preview to show the masked destination, protocol identity, structured-result schema and actual CALL-E task.
- Show the official SDK integration test separately from the simulation. It uses a local HTTP server and does not place an external phone call.

## Replacement narration for the decision segment

> This demonstration uses synthetic outcomes and places no phone calls. The decision rule was fixed before any answer arrived. We begin with six confirmations and two contradictions: eight countable interviews, with fewer than three contradictions, so the hypothesis is provisionally supported under this rule. A voicemail is recorded but contributes nothing to the completed count. One additional corroborated contradiction reaches the frozen limit of three. The hypothesis is now weakened, even though the six supporting answers remain. The operator cannot erase contrary evidence or quietly change the rule after seeing the result.

## Evidence and release status

The current confidence-validation revision passes 92 tests at 91.75% coverage. It rejects NaN, infinities and out-of-range confidence before routing provider results. [Merged fix](https://github.com/yangyangnovelist-hub/countersignal-calle/pull/1).

The [CALL-E contribution](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/198) is merged. A maintainer merge is evidence of a reviewed contribution, not a prize result or customer validation.

No public successful real-provider run was verified during this review. The synthetic console and local SDK integration test must remain labeled separately from external phone execution. See [LIVE-VALIDATION.md](../LIVE-VALIDATION.md) for the consented real-call protocol.

The legacy subtitle source says eight answered interviews with five supporting signals are supported. That sentence conflicts with the Python policy. Do not publish that segment unchanged. This document supplies the corrected example; it does not certify that an existing uploaded video has been replaced. Recording and browser verification remain required before updating the Devpost video.
