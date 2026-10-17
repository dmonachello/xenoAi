from __future__ import annotations

import pytest

from xenosculpt.comfyui.client import (
    ComfyClient,
    ComfyClientError,
    ComfyHttpError,
    ComfyPromptRejected,
)


def test_client_defaults_to_loopback_servers() -> None:
    assert ComfyClient("http://127.0.0.1:8188").origin == "http://127.0.0.1:8188"
    with pytest.raises(ComfyClientError, match="explicit opt-in"):
        ComfyClient("https://example.com")


@pytest.mark.parametrize(
    "origin",
    [
        "ftp://127.0.0.1:8188",
        "http://user:secret@127.0.0.1:8188",
        "http://127.0.0.1:8188/base",
        "http://127.0.0.1:8188?query=yes",
    ],
)
def test_client_rejects_unsafe_or_ambiguous_origins(origin: str) -> None:
    with pytest.raises(ComfyClientError):
        ComfyClient(origin)


class HistoryClient(ComfyClient):
    def __init__(self, response: dict[str, object]) -> None:
        super().__init__("http://127.0.0.1:8188")
        self.response = response

    def _json(self, route: str, *, value=None):
        return self.response


def test_error_history_is_terminal_even_when_completed_is_false() -> None:
    client = HistoryClient(
        {
            "prompt-1": {
                "status": {"status_str": "error", "completed": False},
                "outputs": {},
            }
        }
    )

    history = client.history("prompt-1")

    assert history is not None
    assert history.completed is True
    assert history.success is False


class RejectionClient(ComfyClient):
    def __init__(self) -> None:
        super().__init__("http://127.0.0.1:8188")

    def _json(self, route: str, *, value=None):
        raise ComfyHttpError(400, '{"error":{"type":"invalid_prompt"}}')


def test_http_400_prompt_response_is_a_definite_rejection() -> None:
    with pytest.raises(ComfyPromptRejected) as captured:
        RejectionClient().submit({"prompt_id": "one", "prompt": {}})
    assert captured.value.details["error"]["type"] == "invalid_prompt"
