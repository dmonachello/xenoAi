"""Bounded OpenAI Responses transports."""

from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import BinaryIO

from .storage import Secret


_MAX_STREAM_BYTES = 2_000_000
_MAX_EVENT_BYTES = 1_200_000


class OpenAITransportError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CompletedTextResponse:
    response_id: str
    model: str
    text: str


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_MODELS_URL = "https://api.openai.com/v1/models"


def build_chatgpt_payload(
    *, model: str, instructions: str, prompt: str, schema: dict[str, object]
) -> dict[str, object]:
    return {
        "model": model,
        "instructions": instructions,
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
        "store": False,
        "stream": True,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "xenodream_creation_recipe",
                "strict": True,
                "schema": schema,
            }
        },
    }


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise OpenAITransportError(f"duplicate JSON key in response event: {key}")
        result[key] = value
    return result


def decode_sse_response(
    stream: BinaryIO, *, max_bytes: int = _MAX_STREAM_BYTES
) -> dict[str, object]:
    total = 0
    event_lines: list[bytes] = []
    completed: dict[str, object] | None = None
    terminal_count = 0

    def process(lines: list[bytes]) -> None:
        nonlocal completed, terminal_count
        if not lines:
            return
        kind: str | None = None
        data_parts: list[bytes] = []
        event_size = 0
        for raw in lines:
            event_size += len(raw)
            if event_size > _MAX_EVENT_BYTES:
                raise OpenAITransportError("OpenAI response event exceeded its size limit")
            if raw.startswith(b":"):
                continue
            if raw.startswith(b"event:"):
                kind = raw[6:].strip().decode("ascii", errors="strict")
            elif raw.startswith(b"data:"):
                data_parts.append(raw[5:].lstrip())
        if not data_parts:
            return
        data = b"\n".join(data_parts)
        if data == b"[DONE]":
            return
        try:
            value = json.loads(data, object_pairs_hook=_strict_object)
        except OpenAITransportError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise OpenAITransportError(f"OpenAI returned malformed SSE JSON: {error}") from error
        if not isinstance(value, dict):
            raise OpenAITransportError("OpenAI response event must be a JSON object")
        actual_kind = value.get("type")
        if isinstance(actual_kind, str):
            if kind is not None and actual_kind != kind:
                raise OpenAITransportError("OpenAI response event type mismatch")
            kind = actual_kind
        if kind in {"response.failed", "response.incomplete", "error"}:
            terminal_count += 1
            raise OpenAITransportError(f"OpenAI response ended with {kind}")
        if kind == "response.completed":
            terminal_count += 1
            if terminal_count != 1 or completed is not None:
                raise OpenAITransportError("OpenAI returned more than one terminal event")
            response = value.get("response")
            if not isinstance(response, dict):
                raise OpenAITransportError("response.completed has no response object")
            completed = response

    while True:
        line = stream.readline()
        if not line:
            process(event_lines)
            break
        total += len(line)
        if total > max_bytes:
            raise OpenAITransportError("OpenAI response stream exceeded its size limit")
        stripped = line.rstrip(b"\r\n")
        if stripped == b"":
            process(event_lines)
            event_lines = []
        else:
            event_lines.append(stripped)
    if completed is None:
        raise OpenAITransportError("OpenAI response ended before response.completed")
    return completed


def decode_completed_response(response: dict[str, object]) -> CompletedTextResponse:
    if response.get("status") != "completed":
        raise OpenAITransportError("OpenAI response was not completed")
    response_id = response.get("id")
    model = response.get("model")
    output = response.get("output")
    if not isinstance(response_id, str) or not response_id:
        raise OpenAITransportError("OpenAI response has no id")
    if not isinstance(model, str) or not model:
        raise OpenAITransportError("OpenAI response has no model")
    if not isinstance(output, list):
        raise OpenAITransportError("OpenAI response has no output list")
    texts: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    texts.append(text)
    if len(texts) != 1:
        raise OpenAITransportError("OpenAI response must contain exactly one output_text")
    return CompletedTextResponse(response_id, model, texts[0])


def request_chatgpt_structured(
    *,
    authorization: Secret,
    model: str,
    instructions: str,
    prompt: str,
    schema: dict[str, object],
    timeout_seconds: float,
) -> CompletedTextResponse:
    payload = build_chatgpt_payload(
        model=model, instructions=instructions, prompt=prompt, schema=schema
    )
    request = Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {authorization.reveal()}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "xenosculpt-chatgpt-plan/1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            completed = decode_sse_response(response)
    except HTTPError as error:
        detail = error.read(4096).decode("utf-8", errors="replace")
        raise OpenAITransportError(
            f"OpenAI Responses API returned HTTP {error.code}: {detail}"
        ) from error
    except OpenAITransportError:
        raise
    except (URLError, TimeoutError, OSError) as error:
        raise OpenAITransportError(f"OpenAI Responses API request failed: {error}") from error
    return decode_completed_response(completed)


def list_chatgpt_models(
    authorization: Secret, *, timeout_seconds: float = 30
) -> tuple[str, ...]:
    request = Request(
        OPENAI_MODELS_URL,
        headers={
            "Authorization": f"Bearer {authorization.reveal()}",
            "User-Agent": "xenosculpt-chatgpt-plan/1",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            data = response.read(1_000_001)
    except HTTPError as error:
        detail = error.read(4096).decode("utf-8", errors="replace")
        raise OpenAITransportError(
            f"OpenAI models request returned HTTP {error.code}: {detail}"
        ) from error
    except (URLError, TimeoutError, OSError) as error:
        raise OpenAITransportError(f"OpenAI models request failed: {error}") from error
    if len(data) > 1_000_000:
        raise OpenAITransportError("OpenAI models response exceeded its size limit")
    try:
        value = json.loads(data, object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OpenAITransportError(f"OpenAI models response was invalid: {error}") from error
    if not isinstance(value, dict) or not isinstance(value.get("data"), list):
        raise OpenAITransportError("OpenAI models response has no data array")
    models: list[str] = []
    for item in value["data"]:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            models.append(item["id"])
    if not models:
        raise OpenAITransportError("OpenAI returned no available models")
    return tuple(models)
