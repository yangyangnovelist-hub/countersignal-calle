import copy

import pytest

from countersignal.models import mask_phone, parse_request
from countersignal.policy import (
    build_task,
    call_arguments,
    decision_from_counts,
    idempotency_key,
    preview,
    protocol_hash,
    redact,
    result_schema,
    route_result,
    simulated_result,
    valid_result,
)

RAW = {
    "experiment_id": "smallbet-permit-ops-v1",
    "caller_business_name": "CounterSignal Research",
    "hypothesis": (
        "Permit-status ambiguity recurs often enough that contractors already spend operator time "
        "on a manual workaround."
    ),
    "participant_segment": (
        "Small and midsize US commercial contractors that directly manage municipal permits"
    ),
    "participant_phone": "+15555550123",
    "authorized_research_contact": True,
    "questions": [
        "Tell me about the last time a permit status was unclear or did not match what your team "
        "expected.",
        "What did your team do to resolve it?",
        "Roughly how often has that kind of follow-up happened in the last month?",
        "What happens operationally if nobody follows up?",
        "Who or what currently keeps track of those exceptions?",
    ],
    "decision_rule": {
        "target_completed_interviews": 8,
        "support_minimum": 5,
        "contradiction_limit": 3,
    },
    "region": "US",
    "locale": "en-US",
}


def provider(request, scenario="contradiction"):
    simulated = simulated_result(request, scenario)
    structured = simulated["structured_result"]
    return {
        "id": "call-001",
        "status": "completed",
        "task_completed": scenario != "voicemail",
        "completion_confidence": {"score": 0.95, "label": "high"},
        "structured_result": structured,
        "evidence": ["Recipient-side transcript captured."],
        "metadata": call_arguments(request)["metadata"],
        "recipients": [
            {
                "phone": request.participant_phone,
                "attempts": [
                    {
                        "transcript_turns": [
                            {"speaker": "recipient", "text": structured["verbatim_evidence"]}
                        ]
                    }
                ],
            }
        ],
    }


def test_request_freezes_protocol_and_masks_phone():
    request = parse_request(RAW)
    assert request.questions[2].startswith("Roughly how often")
    assert request.decision_rule.contradiction_limit == 3
    assert request.public_dict()["participant_phone"] == "+15******123"
    assert mask_phone(request.participant_phone) == "+15******123"
    assert protocol_hash(request) == protocol_hash(parse_request(copy.deepcopy(RAW)))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("experiment_id", "bad id", "unsupported"),
        ("participant_phone", "555", "E.164"),
        ("authorized_research_contact", False, "must be true"),
        ("region", "usa", "uppercase"),
        ("locale", "english", "look like"),
        ("hypothesis", "api key secret", "credentials"),
        ("participant_segment", "person@example.com contractors", "contact data"),
    ],
)
def test_request_rejects_unsafe_or_malformed_fields(field, value, message):
    raw = copy.deepcopy(RAW)
    raw[field] = value
    with pytest.raises(ValueError, match=message):
        parse_request(raw)


def test_request_rejects_mutable_or_invalid_question_protocol():
    raw = copy.deepcopy(RAW)
    raw["questions"] = raw["questions"][:4]
    with pytest.raises(ValueError, match="exactly five"):
        parse_request(raw)
    raw = copy.deepcopy(RAW)
    raw["questions"][4] = raw["questions"][0]
    with pytest.raises(ValueError, match="unique"):
        parse_request(raw)
    raw = copy.deepcopy(RAW)
    raw["decision_rule"]["extra"] = 1
    with pytest.raises(ValueError, match="three frozen"):
        parse_request(raw)
    raw = copy.deepcopy(RAW)
    raw["decision_rule"]["support_minimum"] = 7
    with pytest.raises(ValueError, match="cannot exceed"):
        parse_request(raw)


def test_task_is_non_leading_consent_first_and_uses_all_questions():
    request = parse_request(RAW)
    task = build_task(request)
    assert "AI research assistant" in task
    assert "Do not disclose the hypothesis" in task
    assert "without adding leading follow-ups" in task
    assert "product-market fit" in task
    assert all(question in task for question in request.questions)


def test_call_arguments_make_calle_load_bearing_and_stable():
    request = parse_request(RAW)
    arguments = call_arguments(request)
    assert arguments["recipients"][0]["phones"] == [RAW["participant_phone"]]
    assert arguments["metadata"]["workflow_type"] == "frozen_customer_discovery"
    assert arguments["metadata"]["protocol_hash"] == protocol_hash(request)
    assert result_schema()["additionalProperties"] is False
    assert idempotency_key(request).startswith("countersignal-")


@pytest.mark.parametrize(
    ("confirmations", "contradictions", "expected"),
    [
        (0, 0, "collecting"),
        (5, 2, "collecting"),
        (5, 3, "hypothesis_weakened"),
        (5, 0, "collecting"),
        (5, 3, "hypothesis_weakened"),
        (6, 2, "hypothesis_supported_under_rule"),
        (4, 4, "hypothesis_weakened"),
    ],
)
def test_frozen_decision_rule(confirmations, contradictions, expected):
    assert (
        decision_from_counts(
            parse_request(RAW),
            confirmations=confirmations,
            contradictions=contradictions,
        )
        == expected
    )
    with pytest.raises(ValueError, match="negative"):
        decision_from_counts(parse_request(RAW), confirmations=-1, contradictions=0)


@pytest.mark.parametrize("scenario", ["confirmation", "contradiction"])
def test_route_accepts_only_corroborated_classifiable_recipient_evidence(scenario):
    request = parse_request(RAW)
    routed = route_result(request, provider(request, scenario), expected_call_id="call-001")
    assert routed["outcome"] == scenario
    assert routed["counts_toward_completed"] is True
    assert "product-market-fit" in routed["claim_boundary"]


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda value: value.update(status="queued"), "terminal"),
        (lambda value: value.update(completion_confidence={"score": 0.2}), "terminal"),
        (lambda value: value.update(structured_result={}), "schema"),
        (lambda value: value.update(metadata={}), "frozen approved"),
        (lambda value: value.update(id="different"), "frozen approved"),
        (lambda value: value.update(evidence=[]), "frozen approved"),
        (lambda value: value["recipients"][0].update(phone="+15555550999"), "frozen approved"),
        (
            lambda value: value["structured_result"].update(
                consented_after_ai_disclosure="no"
            ),
            "Consent",
        ),
        (
            lambda value: value["structured_result"].update(
                verbatim_evidence="Different uncorroborated words"
            ),
            "corroborated",
        ),
    ],
)
def test_route_fails_closed_for_unreliable_or_unbound_results(mutation, reason):
    request = parse_request(RAW)
    value = provider(request)
    mutation(value)
    routed = route_result(request, value, expected_call_id="call-001")
    assert routed["outcome"] == "unknown"
    assert routed["counts_toward_completed"] is False
    assert reason in routed["reason"]


@pytest.mark.parametrize("scenario", ["ambiguous", "voicemail"])
def test_unknown_scenarios_never_pad_denominator(scenario):
    result = simulated_result(parse_request(RAW), scenario)
    assert result["decision"]["outcome"] == "unknown"
    assert result["decision"]["counts_toward_completed"] is False


def test_preview_is_zero_call_and_redacts_sensitive_output():
    request = parse_request(RAW)
    value = preview(request)
    assert value["creates_phone_call"] is False
    assert RAW["participant_phone"] not in str(value)
    redacted = redact(
        {"nested": ["call +15555550123", "email person@example.com", "api key: abc123"]}
    )
    assert "+15555550123" not in str(redacted)
    assert "person@example.com" not in str(redacted)
    assert "abc123" not in str(redacted)


def test_valid_result_rejects_extra_fields_invalid_enums_and_empty_quote():
    request = parse_request(RAW)
    value = provider(request)["structured_result"]
    assert valid_result(value)
    invalid = {**value, "extra": "no"}
    assert not valid_result(invalid)
    invalid = {**value, "answer_class": "wishful"}
    assert not valid_result(invalid)
    invalid = {**value, "verbatim_evidence": ""}
    assert not valid_result(invalid)


@pytest.mark.parametrize("wrapped", [False, True], ids=["scalar", "score-object"])
@pytest.mark.parametrize(
    ("score", "accepted"),
    [
        pytest.param(float("nan"), False, id="nan"),
        pytest.param(float("inf"), False, id="positive-infinity"),
        pytest.param(float("-inf"), False, id="negative-infinity"),
        pytest.param(1.01, False, id="above-probability-range"),
        pytest.param(-0.01, False, id="below-probability-range"),
        pytest.param(10**400, False, id="integer-overflow"),
        pytest.param(True, False, id="boolean"),
        pytest.param("0.95", False, id="numeric-string"),
        pytest.param(None, False, id="missing-score"),
        pytest.param({"score": None}, False, id="nested-missing-score"),
        pytest.param(0, False, id="zero"),
        pytest.param(0.799999, False, id="below-threshold"),
        pytest.param(0.8, True, id="at-threshold"),
        pytest.param(0.95, True, id="normal-confidence"),
        pytest.param(1, True, id="one"),
    ],
)
def test_provider_confidence_must_be_a_bounded_probability(score, accepted, wrapped):
    request = parse_request(RAW)
    response = provider(request)
    response["completion_confidence"] = {"score": score, "label": "high"} if wrapped else score
    decision = route_result(request, response, expected_call_id=response["id"])
    assert decision["outcome"] == ("contradiction" if accepted else "unknown")
    assert decision["counts_toward_completed"] is accepted
