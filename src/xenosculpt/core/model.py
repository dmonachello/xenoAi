"""Application-neutral project values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar


MutationT = TypeVar("MutationT")


@dataclass(frozen=True, slots=True)
class ApplicationIdentity:
    name: str
    document_kind: str
    artifact_suffix: str

    def __post_init__(self) -> None:
        if not self.name or not self.document_kind:
            raise ValueError("application identity values must be non-empty")
        suffix = self.artifact_suffix
        if (
            not suffix.startswith(".")
            or len(suffix) == 1
            or "/" in suffix
            or "\\" in suffix
        ):
            raise ValueError("artifact suffix must be a simple file extension")


@dataclass(frozen=True, slots=True)
class Revision:
    id: str
    parent_id: str | None
    artifact_sha256: str
    created_at: str
    operation: str
    message: str
    prompt: str | None
    details: dict[str, object]


@dataclass(frozen=True, slots=True)
class ApplyResult(Generic[MutationT]):
    revision: Revision
    created: bool
    mutation: MutationT | None


@dataclass(frozen=True, slots=True)
class ArtifactInfo:
    path: str
    bytes: int
    sha256: str
    revision_id: str
