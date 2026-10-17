"""Bounded local HTTP client for ComfyUI's prompt API."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ComfyClientError(RuntimeError):
    pass


class ComfyHttpError(ComfyClientError):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"ComfyUI returned HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


class ComfyPromptRejected(ComfyClientError):
    def __init__(self, details: dict[str, Any]) -> None:
        super().__init__("ComfyUI rejected the prompt")
        self.details = details


@dataclass(frozen=True, slots=True)
class ComfySystem:
    version: str
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ComfySubmission:
    prompt_id: str
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ComfyHistory:
    completed: bool
    success: bool
    raw: dict[str, Any]


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ComfyClient:
    def __init__(self, origin: str, *, allow_remote: bool = False, timeout: float = 15) -> None:
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.path not in {"", "/"}:
            raise ComfyClientError("server must be an HTTP origin without a path")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ComfyClientError("server origin may not contain credentials, query, or fragment")
        if not allow_remote and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ComfyClientError("remote ComfyUI servers require explicit opt-in")
        self.origin = origin.rstrip("/")
        self.timeout = timeout
        self._opener = build_opener(_NoRedirect())

    def _request(self, route: str, *, body: bytes | None = None, maximum: int = 8 * 1024 * 1024) -> tuple[bytes, str]:
        request = Request(
            self.origin + route,
            data=body,
            headers={"Content-Type": "application/json"} if body is not None else {},
            method="POST" if body is not None else "GET",
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                data = response.read(maximum + 1)
                media_type = response.headers.get_content_type()
        except HTTPError as error:
            detail = error.read(64 * 1024).decode("utf-8", "replace")
            raise ComfyHttpError(error.code, detail) from error
        except OSError as error:
            raise ComfyClientError(f"ComfyUI request failed: {error}") from error
        if len(data) > maximum:
            raise ComfyClientError("ComfyUI response exceeded the size limit")
        return data, media_type

    def _json(self, route: str, *, value: dict[str, Any] | None = None) -> dict[str, Any]:
        body = (
            None
            if value is None
            else json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
                sort_keys=True,
            ).encode("utf-8")
        )
        data, _ = self._request(route, body=body)
        try:
            result = json.loads(data)
        except json.JSONDecodeError as error:
            raise ComfyClientError("ComfyUI returned invalid JSON") from error
        if not isinstance(result, dict):
            raise ComfyClientError("ComfyUI returned a non-object JSON response")
        return result

    def system_stats(self) -> ComfySystem:
        raw = self._json("/system_stats")
        system = raw.get("system")
        version = system.get("comfyui_version") if isinstance(system, dict) else None
        if not isinstance(version, str):
            raise ComfyClientError("ComfyUI did not report its version")
        return ComfySystem(version, raw)

    def submit(self, request: dict[str, Any]) -> ComfySubmission:
        try:
            raw = self._json("/prompt", value=request)
        except ComfyHttpError as error:
            if error.status != 400:
                raise
            try:
                details = json.loads(error.detail)
            except json.JSONDecodeError:
                details = {"http_status": 400, "body": error.detail}
            if not isinstance(details, dict):
                details = {"http_status": 400, "body": details}
            raise ComfyPromptRejected(details) from error
        prompt_id = raw.get("prompt_id")
        if not isinstance(prompt_id, str) or prompt_id != request.get("prompt_id"):
            raise ComfyClientError("ComfyUI returned a different prompt ID")
        return ComfySubmission(prompt_id, raw)

    def history(self, prompt_id: str) -> ComfyHistory | None:
        raw = self._json(f"/history/{prompt_id}")
        item = raw.get(prompt_id)
        if item is None:
            return None
        if not isinstance(item, dict):
            raise ComfyClientError("ComfyUI history entry is invalid")
        status = item.get("status", {})
        if not isinstance(status, dict):
            raise ComfyClientError("ComfyUI history status is invalid")
        status_name = status.get("status_str")
        terminal = bool(status.get("completed")) or status_name in {"success", "error"}
        success = terminal and status_name == "success"
        return ComfyHistory(terminal, success, item)

    def download(self, locator: dict[str, str]) -> tuple[bytes, str]:
        query = urlencode({key: locator[key] for key in ("filename", "subfolder", "type")})
        return self._request(f"/view?{query}", maximum=128 * 1024 * 1024)
