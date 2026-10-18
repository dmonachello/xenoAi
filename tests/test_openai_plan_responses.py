from __future__ import annotations

from io import BytesIO
import json

import pytest

from xenosculpt_openai.responses import (
    OpenAITransportError,
    build_chatgpt_payload,
    decode_completed_response,
    decode_sse_response,
)


def _response(*, status: str = "completed") -> dict[str, object]:
    return {
        "id": "resp_test",
        "model": "test-model",
        "status": status,
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"seed":"cube","recipe":"","summary":"cube","unsupported":[]}',
                    }
                ],
            }
        ],
    }


def _event(kind: str, value: dict[str, object]) -> bytes:
    return (
        f"event: {kind}\r\ndata: "
        + json.dumps(value, separators=(",", ":"))
        + "\r\n\r\n"
    ).encode("utf-8")


def test_chatgpt_payload_obeys_plan_usage_contract() -> None:
    payload = build_chatgpt_payload(
        model="test-model",
        instructions="translate",
        prompt="make a cube",
        schema={"type": "object"},
    )

    assert payload["store"] is False
    assert payload["stream"] is True
    assert payload["input"] == [
        {"role": "user", "content": [{"type": "input_text", "text": "make a cube"}]}
    ]
    assert "max_output_tokens" not in payload
    assert "temperature" not in payload


def test_sse_requires_one_completed_terminal_response() -> None:
    completed = _response()
    stream = BytesIO(
        _event("response.created", {"type": "response.created", "response": {"id": "resp_test"}})
        + _event("response.completed", {"type": "response.completed", "response": completed})
    )

    assert decode_sse_response(stream) == completed


@pytest.mark.parametrize("kind", ["response.failed", "response.incomplete", "error"])
def test_sse_rejects_failure_terminals(kind: str) -> None:
    with pytest.raises(OpenAITransportError):
        decode_sse_response(
            BytesIO(_event(kind, {"type": kind, "response": _response(status="failed")}))
        )


def test_sse_rejects_eof_and_duplicate_completion() -> None:
    with pytest.raises(OpenAITransportError, match="before response.completed"):
        decode_sse_response(BytesIO(_event("response.created", {"type": "response.created"})))

    terminal = _event(
        "response.completed", {"type": "response.completed", "response": _response()}
    )
    with pytest.raises(OpenAITransportError, match="more than one terminal"):
        decode_sse_response(BytesIO(terminal + terminal))


def test_completed_decoder_rejects_failed_response_with_valid_looking_output() -> None:
    with pytest.raises(OpenAITransportError, match="not completed"):
        decode_completed_response(_response(status="failed"))


def test_completed_decoder_returns_only_output_text() -> None:
    value = decode_completed_response(_response())
    assert value.response_id == "resp_test"
    assert value.model == "test-model"
    assert value.text.startswith('{"seed"')
