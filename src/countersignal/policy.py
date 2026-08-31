"""Frozen interview protocol, strict result schema, and contradiction-first routing."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from typing import Any

from countersignal.models import ExperimentRequest

TERMINAL_SUCCESS = {"completed", "succeeded"}
MIN_CONFIDENCE = 0.8
RECIPIENT_SPEAKERS = {"recipient", "user", "callee"}
PHONE_LIKE = re.compile(r"(?<!\w)\+?[1-9]\d{7,14}(?!\w)")
EMAIL_LIKE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TOKEN_LIKE = re.compile(
    r"(?i)\b(bearer|token|api[_ -]?key|access[_ -]?token|password|private[_ -]?key|"
    r"client[_ -]?secret|secret|credential)\b\s*[:=]?\s*\S+"
)


def result_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "consented_after_ai_disclosure",
            "participant_matches_segment",
            "answer_class",
            "verbatim_evidence",
            "reason_summary",
            "willing_to_follow_up",
        ],
        "properties": {
            "consented_after_ai_disclosure": {
                "type": "string",
                "enum": ["yes", "no", "unknown"],
            },
            "participant_matches_segment": {
                "type": "string",
                "enum": ["yes", "no", "unknown"],
            },
            "answer_class": {
                "type": "string",
                "enum": ["confirmation", "contradiction", "ambiguous", "no_response"],
            },
            "verbatim_evidence": {"type": "string", "maxLength": 300},
            "reason_summary": {"type": "string", "maxLength": 300},
            "willing_to_follow_up": {
                "type": "string",
                "enum": ["yes", "no", "unknown"],
            },
        },
        "additionalProperties": False,
    }


def frozen_protocol(request: ExperimentRequest) -> dict[str, Any]:
    return {
        "experiment_id": request.experiment_id,
        "caller_business_name": request.caller_business_name,
        "hypothesis": request.hypothesis,
        "participant_segment": request.participant_segment,
        "questions": list(request.questions),
        "decision_rule": asdict(request.decision_rule),
    }


def protocol_hash(request: ExperimentRequest) -> str:
    canonical = json.dumps(
        frozen_protocol(request), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def build_task(request: ExperimentRequest) -> str:
    numbered = " ".join(
        f"Question {index}: {question}" for index, question in enumerate(request.questions, 1)
    )
    return (
        f"Call one authorized research participant on behalf of {request.caller_business_name}. "
        f"Speak in locale {request.locale}. Identify yourself as an AI research assistant and ask "
        "for consent to a short customer-discovery interview. Do not disclose the hypothesis, "
        "pitch, persuade, coach, sell, collect names, or request credentials, payment data, or "
        "personal contact details. If consent is not clearly yes, end the call without asking the "
        "research questions. First confirm the participant matches this segment: "
        f"{request.participant_segment}. Then ask these exact pre-registered questions in order, "
        f"without adding leading follow-ups: {numbered} Classify the evidence as confirmation only "
        "when the participant describes the hypothesized pain from their own experience; classify "
        "it as contradiction when their experience rejects the pain or already solves it; "
        "otherwise "
        "use ambiguous or no_response. Capture one short verbatim participant quote. The frozen "
        f"hypothesis is: {request.hypothesis} Do not claim product-market fit or change the frozen "
        "decision rule."
    )


def call_arguments(request: ExperimentRequest) -> dict[str, Any]:
    return {
        "task": build_task(request),
        "recipients": [
            {
                "phones": [request.participant_phone],
                "region": request.region,
                "locale": request.locale,
            }
        ],
        "result_schema": result_schema(),
        "metadata": {
            "workflow_type": "frozen_customer_discovery",
            "experiment_id": request.experiment_id,
            "protocol_hash": protocol_hash(request),
        },
    }


def idempotency_key(request: ExperimentRequest) -> str:
    canonical = json.dumps(
        call_arguments(request), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return f"countersignal-{hashlib.sha256(canonical).hexdigest()}"


def confidence_score(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        score = value.get("score")
        if isinstance(score, (int, float)) and not isinstance(score, bool):
            return float(score)
    return 0.0


def valid_result(value: Any) -> bool:
    schema = result_schema()
    if not isinstance(value, dict) or set(value) != set(schema["required"]):
        return False
    for field, rule in schema["properties"].items():
        item = value[field]
        if not isinstance(item, str) or len(item) > rule.get("maxLength", 10_000):
            return False
        if "enum" in rule and item not in rule["enum"]:
            return False
    answer_class = value["answer_class"]
    return not (
        answer_class in {"confirmation", "contradiction"}
        and len(value["verbatim_evidence"].strip()) < 4
    )


def _recipient_transcript(provider_result: dict[str, Any], destination: str) -> str:
    recipients = provider_result.get("recipients")
    if not isinstance(recipients, list) or len(recipients) != 1:
        return ""
    recipient = recipients[0]
    if not isinstance(recipient, dict) or recipient.get("phone") != destination:
        return ""
    turns: list[str] = []
    for attempt in recipient.get("attempts", []):
        if not isinstance(attempt, dict):
            continue
        for turn in attempt.get("transcript_turns", []):
            if (
                isinstance(turn, dict)
                and str(turn.get("speaker", "")).lower() in RECIPIENT_SPEAKERS
                and isinstance(turn.get("text"), str)
            ):
                turns.append(turn["text"])
    return "\n".join(turns)


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())


def _quote_corroborated(quote: str, transcript: str) -> bool:
    expected = _tokens(quote)
    observed = _tokens(transcript)
    if len(expected) < 2:
        return False
    width = len(expected)
    return any(
        observed[index : index + width] == expected
        for index in range(len(observed) - width + 1)
    )


def decision_from_counts(
    request: ExperimentRequest,
    *,
    confirmations: int,
    contradictions: int,
) -> str:
    if min(confirmations, contradictions) < 0:
        raise ValueError("counts cannot be negative")
    if contradictions >= request.decision_rule.contradiction_limit:
        return "hypothesis_weakened"
    completed = confirmations + contradictions
    if completed < request.decision_rule.target_completed_interviews:
        return "collecting"
    if confirmations >= request.decision_rule.support_minimum:
        return "hypothesis_supported_under_rule"
    return "inconclusive"


def route_result(
    request: ExperimentRequest,
    provider_result: dict[str, Any],
    *,
    expected_call_id: str | None = None,
) -> dict[str, Any]:
    unknown = {
        "outcome": "unknown",
        "counts_toward_completed": False,
        "claim_boundary": "Operational research signal, not product-market-fit evidence.",
    }
    if (
        provider_result.get("status") not in TERMINAL_SUCCESS
        or provider_result.get("task_completed") is not True
        or confidence_score(provider_result.get("completion_confidence")) < MIN_CONFIDENCE
    ):
        return {**unknown, "reason": "CALL-E did not return a reliable terminal success."}
    structured = provider_result.get("structured_result")
    if not valid_result(structured):
        return {**unknown, "reason": "CALL-E did not return the complete result schema."}
    assert isinstance(structured, dict)
    expected_metadata = {
        "workflow_type": "frozen_customer_discovery",
        "experiment_id": request.experiment_id,
        "protocol_hash": protocol_hash(request),
    }
    transcript = _recipient_transcript(provider_result, request.participant_phone)
    evidence = provider_result.get("evidence")
    if (
        provider_result.get("metadata") != expected_metadata
        or (expected_call_id is not None and provider_result.get("id") != expected_call_id)
        or not isinstance(evidence, list)
        or not any(isinstance(item, str) and item.strip() for item in evidence)
        or not transcript
    ):
        return {**unknown, "reason": "Evidence was not bound to the frozen approved call."}
    if (
        structured["consented_after_ai_disclosure"] != "yes"
        or structured["participant_matches_segment"] != "yes"
    ):
        return {**unknown, "reason": "Consent or segment membership was not confirmed."}
    answer_class = structured["answer_class"]
    if answer_class not in {"confirmation", "contradiction"}:
        return {**unknown, "reason": "The interview did not produce classifiable evidence."}
    if not _quote_corroborated(structured["verbatim_evidence"], transcript):
        return {**unknown, "reason": "The classified quote was not corroborated by the recipient."}
    return {
        "outcome": answer_class,
        "counts_toward_completed": True,
        "reason": "Consent-bound recipient evidence supports the provisional classification.",
        "claim_boundary": "Operational research signal, not product-market-fit evidence.",
    }


def redact(value: Any) -> Any:
    if isinstance(value, str):
        value = PHONE_LIKE.sub("[phone-redacted]", value)
        value = EMAIL_LIKE.sub("[email-redacted]", value)
        return TOKEN_LIKE.sub("[credential-redacted]", value)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    return value


def preview(request: ExperimentRequest) -> dict[str, Any]:
    arguments = call_arguments(request)
    arguments["recipients"][0]["phones"] = [request.public_dict()["participant_phone"]]
    return {
        "mode": "preview",
        "creates_phone_call": False,
        "frozen_protocol": frozen_protocol(request),
        "protocol_hash": protocol_hash(request),
        "idempotency_key": idempotency_key(request),
        "call_arguments": arguments,
        "decision_authority": "The frozen 8/5/3 rule; classifications remain reviewable.",
    }


def simulated_result(request: ExperimentRequest, scenario: str) -> dict[str, Any]:
    examples = {
        "confirmation": {
            "answer_class": "confirmation",
            "verbatim_evidence": "We lose hours calling the permit office every week",
            "reason_summary": "The participant reports repeated manual phone work.",
        },
        "contradiction": {
            "answer_class": "contradiction",
            "verbatim_evidence": "Our expeditor already handles every permit status call",
            "reason_summary": "The participant already has a satisfactory workaround.",
        },
        "ambiguous": {
            "answer_class": "ambiguous",
            "verbatim_evidence": "It depends on the project",
            "reason_summary": "The response does not support a reliable classification.",
        },
        "voicemail": {
            "answer_class": "no_response",
            "verbatim_evidence": "",
            "reason_summary": "The call reached voicemail.",
        },
    }
    selected = examples[scenario]
    structured = {
        "consented_after_ai_disclosure": "yes" if scenario != "voicemail" else "unknown",
        "participant_matches_segment": "yes" if scenario != "voicemail" else "unknown",
        **selected,
        "willing_to_follow_up": "yes" if scenario == "confirmation" else "no",
    }
    provider = {
        "id": "simulation-call",
        "status": "completed",
        "task_completed": scenario != "voicemail",
        "completion_confidence": {"score": 0.95, "label": "high"},
        "structured_result": structured,
        "evidence": ["Synthetic no-call evidence for deterministic route testing."],
        "metadata": call_arguments(request)["metadata"],
        "recipients": [
            {
                "phone": request.participant_phone,
                "attempts": [
                    {
                        "transcript_turns": [
                            {"speaker": "recipient", "text": selected["verbatim_evidence"]}
                        ]
                    }
                ],
            }
        ],
    }
    return {
        "mode": "simulate",
        "creates_phone_call": False,
        "scenario": scenario,
        "structured_result": structured,
        "decision": route_result(request, provider, expected_call_id="simulation-call"),
    }
