# Judge guide

## Ninety-second path

1. Open the evidence console and read the frozen hypothesis, segment, questions and 8/5/3 rule.
2. Click **Contradiction** three times and watch the rule return `hypothesis_weakened`.
3. Click **Inspect frozen CALL-E task** to verify AI disclosure, consent, fixed questions, strict
   schema and no-call preview.
4. Inspect the SDK runtime test in `tests/test_sdk_runtime.py` and run the test suite.
5. Review the public live artifact only if it exists; the README never claims one otherwise.

## Four official criteria

- **Real-world impact:** founders can scale discovery without scaling confirmation bias.
- **Quality of idea:** pre-registration makes contradictions load-bearing rather than decorative.
- **Technical implementation:** CALL-E runs through the official SDK with strict schema, evidence
  binding, idempotency and fail-closed routing.
- **Product experience and demo:** one interaction visibly changes the frozen experiment decision.
