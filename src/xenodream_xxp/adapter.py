"""XenoDream native-document behavior used by the revision core."""

from __future__ import annotations

from dataclasses import dataclass

from .diffing import diff_documents
from .document import KeyValueRecord, parse_bytes
from .errors import WorkspaceError
from .mutation import (
    MutationResult,
    VerifiedOperation,
    apply_verified_mutation,
    verified_operation_details,
)
from xenosculpt.core.model import ApplicationIdentity


XENODREAM_APPLICATION = ApplicationIdentity(
    name="xenodream-x",
    document_kind="xenodream/xdx-project/v1",
    artifact_suffix=".xxp",
)


@dataclass(frozen=True, slots=True)
class XenoDreamArtifactDescriptor:
    xdx_version: str


@dataclass(frozen=True, slots=True)
class XenoDreamArtifactMutation:
    data: bytes
    operation: str
    details: dict[str, object]
    result: MutationResult


class XenoDreamArtifactAdapter:
    """Validate, mutate, and compare lossless XDX project bytes."""

    def inspect(self, data: bytes) -> XenoDreamArtifactDescriptor:
        program = self._header_value(data, b"Program")
        if program != "XDX":
            raise WorkspaceError("source must be an XDX project")
        version = self._header_value(data, b"Progversion")
        return XenoDreamArtifactDescriptor(xdx_version=version)

    def validate_import(self, data: bytes) -> None:
        if self._header_value(data, b"Program") != "XDX":
            raise WorkspaceError("import must be an XDX project")

    def apply(
        self, data: bytes, operation: VerifiedOperation
    ) -> XenoDreamArtifactMutation:
        result = apply_verified_mutation(data, operation)
        details = verified_operation_details(operation)
        if result.native_validation_required:
            details.setdefault("native_validation_required", True)
            details.setdefault("fabrication_suitable", False)
        return XenoDreamArtifactMutation(
            data=result.data,
            operation=str(details["type"]),
            details=dict(details),
            result=result,
        )

    def compare(self, before: bytes, after: bytes) -> list[dict[str, object]]:
        return diff_documents(parse_bytes(before), parse_bytes(after))

    @staticmethod
    def _header_value(data: bytes, key: bytes) -> str:
        document = parse_bytes(data)
        if document.to_bytes() != data:
            raise WorkspaceError("artifact failed exact parser round trip")
        matches = [
            record.value
            for record in document.records
            if isinstance(record, KeyValueRecord)
            and record.section == b"Header"
            and record.section_occurrence == 0
            and record.key == key
        ]
        if len(matches) != 1:
            raise WorkspaceError(
                f"artifact must contain one Header.{key.decode()} value"
            )
        try:
            return matches[0].decode("ascii")
        except UnicodeDecodeError as error:
            raise WorkspaceError(f"Header.{key.decode()} must be ASCII") from error
