"""Narrow OpenAI Responses API boundary for XenoDream creation recipes."""

from __future__ import annotations

import json
import math
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .creation import CreationError, CreationRecipe, CreationSeed, ModelCreation
from .mutation import cylinder_metamorph_profiles, sphere_metamorph_profiles


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
_MAX_RESPONSE_BYTES = 1_000_000


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CreationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _loads(data: str | bytes) -> object:
    try:
        return json.loads(data, object_pairs_hook=_strict_object)
    except CreationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CreationError(f"planner returned invalid JSON: {error}") from error


def _instructions() -> str:
    sphere = ", ".join(sphere_metamorph_profiles())
    cylinder = ", ".join(cylinder_metamorph_profiles())
    return f"""You translate a user's XenoDream scene request into a closed recipe.
Return only the required JSON object. Never invent operations, object names, or
profiles. Choose exactly one seed from the schema. The seed object names are:
Cube2, Sphere2, Cylinder2, RoundCube2, Pipe2, Torus2, Cog2, SpiralShell2.

The recipe is either empty, one exact clause, or 2-5 exact clauses separated by
'; '. Allowed clauses are:
- add Cube at X Y Z (Cube seed/composition only; at most Cube3 and Cube4)
- add Sphere at X Y Z (only directly after a one-Cube seed; it becomes Sphere3)
- set object NAME scale to X Y Z
- set object NAME rotation to X Y Z (Cube only)
- set object NAME position to X Y Z
- set object NAME color density to VALUE (Cube only)
- set object NAME face warp to VALUE (Cube only)
- place objects in a centered row with spacing VALUE
- evolve with seed INTEGER and strength VALUE
- apply Sphere profile PROFILE to object NAME
- apply Cylinder profile PROFILE to object NAME

Sphere profiles: {sphere}.
Cylinder profiles: {cylinder}.

Operations execute in order. Use absolute numeric values. Only reference an
object after it exists. Prefer Cube when the request needs a Cube/Sphere or
multi-Cube composition. Closed constructors support scale and position only.
If any requested feature cannot be represented exactly, list it in unsupported;
do not silently omit or approximate it. Summary describes only the admitted
result. Do not mention validation, printability, or fabrication suitability."""


def _schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["seed", "recipe", "summary", "unsupported"],
        "properties": {
            "seed": {"type": "string", "enum": [item.value for item in CreationSeed]},
            "recipe": {"type": "string", "maxLength": 1500},
            "summary": {"type": "string", "minLength": 1, "maxLength": 500},
            "unsupported": {
                "type": "array",
                "maxItems": 12,
                "items": {"type": "string", "minLength": 1, "maxLength": 300},
            },
        },
    }


def decode_creation_response(data: bytes, requested_model: str) -> ModelCreation:
    """Decode one bounded Responses API result into the closed domain type."""

    response = _loads(data)
    if not isinstance(response, dict):
        raise CreationError("planner response must be a JSON object")
    response_id = response.get("id")
    actual_model = response.get("model", requested_model)
    output = response.get("output")
    if not isinstance(output, list):
        raise CreationError("planner response has no output list")
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
        raise CreationError("planner response must contain exactly one output_text")
    value = _loads(texts[0])
    if not isinstance(value, dict) or set(value) != {
        "seed",
        "recipe",
        "summary",
        "unsupported",
    }:
        raise CreationError("planner recipe has unexpected or missing fields")
    unsupported = value["unsupported"]
    if not isinstance(unsupported, list):
        raise CreationError("planner recipe unsupported field must be an array")
    try:
        recipe = CreationRecipe(
            seed=CreationSeed(value["seed"]),
            recipe=value["recipe"],
            summary=value["summary"],
            unsupported=tuple(unsupported),
        )
        return ModelCreation(recipe, actual_model, response_id)
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CreationError):
            raise
        raise CreationError(f"planner recipe is invalid: {error}") from error


def request_creation(
    prompt: str,
    *,
    model: str,
    timeout_seconds: float = 60,
    api_key: str | None = None,
) -> ModelCreation:
    """Request one strict creation recipe from the official Responses API."""

    if not isinstance(prompt, str) or not prompt.strip():
        raise CreationError("prompt must be non-empty text")
    if not isinstance(model, str) or re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", model
    ) is None:
        raise CreationError("model must be a supported ASCII identifier")
    if isinstance(timeout_seconds, bool) or not isinstance(
        timeout_seconds, (int, float)
    ) or not math.isfinite(
        timeout_seconds
    ) or timeout_seconds <= 0:
        raise CreationError("timeout must be finite and positive")
    if len(prompt) > 20_000:
        raise CreationError("prompt exceeds the 20000-character limit")
    key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
    if not key:
        raise CreationError("OPENAI_API_KEY is required")
    payload = {
        "model": model,
        "instructions": _instructions(),
        "input": prompt.strip(),
        "max_output_tokens": 1200,
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "xenodream_creation_recipe",
                "strict": True,
                "schema": _schema(),
            }
        },
    }
    request = Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "xenosculpt-natural-creation/1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            data = response.read(_MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        detail = error.read(4096).decode("utf-8", errors="replace")
        raise CreationError(
            f"OpenAI Responses API returned HTTP {error.code}: {detail}"
        ) from error
    except (URLError, TimeoutError, OSError) as error:
        raise CreationError(f"OpenAI Responses API request failed: {error}") from error
    if len(data) > _MAX_RESPONSE_BYTES:
        raise CreationError("OpenAI response exceeded the 1000000-byte limit")
    return decode_creation_response(data, model)
