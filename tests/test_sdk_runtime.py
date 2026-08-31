"""Prove the published CALL-E SDK performs HTTP at runtime."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from calle import CalleClient

from countersignal.models import parse_request
from countersignal.policy import call_arguments, simulated_result
from countersignal.runtime import execute
from tests.test_policy import RAW


class CaptureHandler(BaseHTTPRequestHandler):
    requests = []
    request_model = parse_request(RAW)

    def log_message(self, format, *args):
        return

    def send_payload(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length))
        type(self).requests.append(
            {
                "method": "POST",
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "idempotency_key": self.headers.get("Idempotency-Key"),
                "payload": payload,
            }
        )
        self.send_payload(201, {"id": "call_sdk_001", "status": "queued"})

    def do_GET(self):
        type(self).requests.append({"method": "GET", "path": self.path})
        request = type(self).request_model
        structured = simulated_result(request, "contradiction")["structured_result"]
        self.send_payload(
            200,
            {
                "id": "call_sdk_001",
                "status": "completed",
                "task_completed": True,
                "completion_confidence": {"score": 0.96, "label": "high"},
                "structured_result": structured,
                "evidence": ["Recipient transcript captured."],
                "metadata": call_arguments(request)["metadata"],
                "recipients": [
                    {
                        "phone": request.participant_phone,
                        "attempts": [
                            {
                                "transcript_turns": [
                                    {
                                        "speaker": "recipient",
                                        "text": structured["verbatim_evidence"],
                                    }
                                ]
                            }
                        ],
                    }
                ],
            },
        )


def test_published_sdk_posts_and_polls_real_http():
    CaptureHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), CaptureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    request = parse_request(RAW)
    try:
        with CalleClient(
            api_key="calle_test_capture",
            base_url=f"http://127.0.0.1:{server.server_port}",
        ) as sdk:
            result = execute(request, sdk.calls, timeout_seconds=5)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert [item["method"] for item in CaptureHandler.requests] == ["POST", "GET"]
    create = CaptureHandler.requests[0]
    assert create["path"] == "/v1/calls"
    assert create["authorization"] == "Bearer calle_test_capture"
    assert create["idempotency_key"].startswith("countersignal-")
    assert create["payload"]["metadata"]["workflow_type"] == "frozen_customer_discovery"
    assert CaptureHandler.requests[1]["path"] == "/v1/calls/call_sdk_001"
    assert result["decision"]["outcome"] == "contradiction"
