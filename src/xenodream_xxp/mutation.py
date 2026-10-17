"""Evidence-gated, byte-preserving mutations of native XDX 1.220 projects."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, DecimalException, ROUND_HALF_EVEN
from functools import lru_cache
from importlib.resources import files
import json
import random
import re
from typing import Any, TypeAlias

from .diffing import diff_documents
from .document import Document, KeyValueRecord, parse_bytes
from .generator import Vector3
from .scene import (
    SceneBinding,
    SceneNode,
    SceneOperation,
    _describe_document,
)


class MutationError(ValueError):
    """A requested edit is ambiguous or outside the verified mutation surface."""


@dataclass(frozen=True, slots=True)
class ObjectMutation:
    """Verified editable properties for one uniquely named object."""

    object_name: str
    scale: Vector3 | None = None
    rotation: Vector3 | None = None
    position: Vector3 | None = None
    color_density: Decimal | None = None
    face_warp: Decimal | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.object_name, str) or not self.object_name:
            raise TypeError("object_name must be a non-empty string")
        for name in ("scale", "rotation", "position"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, Vector3):
                raise TypeError(f"{name} must be Vector3 or None")
        for name in ("color_density", "face_warp"):
            value = getattr(self, name)
            if value is not None:
                if not isinstance(value, Decimal):
                    raise TypeError(f"{name} must be Decimal or None")
                if not value.is_finite():
                    raise MutationError(f"{name} must be finite")
        if all(
            value is None
            for value in (
                self.scale,
                self.rotation,
                self.position,
                self.color_density,
                self.face_warp,
            )
        ):
            raise MutationError("object mutation must change at least one property")


@dataclass(frozen=True, slots=True)
class CenteredRowMutation:
    """Place every supported object at equal X intervals around a center."""

    spacing: Decimal
    center: Vector3 = Vector3()

    def __post_init__(self) -> None:
        if not isinstance(self.spacing, Decimal):
            raise TypeError("spacing must be Decimal")
        if not self.spacing.is_finite():
            raise MutationError("spacing must be finite")
        if not isinstance(self.center, Vector3):
            raise TypeError("center must be Vector3")


@dataclass(frozen=True, slots=True)
class SeededVariation:
    """Derive one repeatable physical-form variation from the current model."""

    seed: int
    strength: Decimal = Decimal("0.35")

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer")
        if self.seed < 0 or self.seed > 2**64 - 1:
            raise MutationError("seed must be between 0 and 2^64-1")
        if not isinstance(self.strength, Decimal):
            raise TypeError("strength must be Decimal")
        if not self.strength.is_finite() or not Decimal("0") < self.strength <= 1:
            raise MutationError("strength must be finite and greater than 0 through 1")


@dataclass(frozen=True, slots=True)
class SphereMetamorphMutation:
    """Apply one measured complete Sphere metamorph profile."""

    object_name: str
    profile: str

    def __post_init__(self) -> None:
        if not isinstance(self.object_name, str) or not self.object_name:
            raise TypeError("object_name must be a non-empty string")
        if not isinstance(self.profile, str) or not self.profile:
            raise TypeError("profile must be a non-empty string")
        if self.profile not in sphere_metamorph_profiles():
            raise MutationError(f"unknown Sphere metamorph profile {self.profile!r}")


@dataclass(frozen=True, slots=True)
class CylinderMetamorphMutation:
    """Apply one measured complete Cylinder metamorph profile."""

    object_name: str
    profile: str

    def __post_init__(self) -> None:
        if not isinstance(self.object_name, str) or not self.object_name:
            raise TypeError("object_name must be a non-empty string")
        if not isinstance(self.profile, str) or not self.profile:
            raise TypeError("profile must be a non-empty string")
        if self.profile not in cylinder_metamorph_profiles():
            raise MutationError(
                f"unknown Cylinder metamorph profile {self.profile!r}"
            )


VerifiedOperation: TypeAlias = (
    ObjectMutation
    | CenteredRowMutation
    | SeededVariation
    | SphereMetamorphMutation
    | CylinderMetamorphMutation
)


@dataclass(frozen=True, slots=True)
class MutationResult:
    data: bytes
    changed: bool
    differences: tuple[dict[str, object], ...]
    object_names: tuple[str, ...]
    native_validation_required: bool = False
    fabrication_suitable: bool = False


@dataclass(frozen=True, slots=True)
class _ObjectRecord:
    section: bytes
    name: str
    kind: str


_AllowedDifference: TypeAlias = tuple[str, int, str, int, int | None]


def _allowed_difference(
    section: bytes, key: str, token_index: int | None
) -> _AllowedDifference:
    return (section.decode(), 0, key, 0, token_index)


_SUPPORTED_SIGNATURES = {
    ("cube",),
    ("cube", "cube"),
    ("cube", "cube", "cube"),
    ("sphere",),
    ("cube", "sphere"),
}


@lru_cache(maxsize=1)
def _sphere_profile_registry() -> dict[str, Any]:
    resource = files("xenodream_xxp").joinpath(
        "data", "xdx-1.220-sphere-mutation-profiles.json"
    )
    registry = json.loads(resource.read_text(encoding="utf-8"))
    if registry.get("schema_version") != 1:
        raise MutationError("unsupported Sphere metamorph profile schema")
    target = registry.get("target")
    if not isinstance(target, dict) or target != {
        "product": "XenoDream X",
        "format_version": "1.220",
        "operation": "Sphere",
        "style": "1",
        "num_pars": 12,
    }:
        raise MutationError("Sphere metamorph profile target is invalid")
    policy = registry.get("policy")
    if policy != {
        "replace_complete_parameter_vector": True,
        "source_profiles_native_evaluated": True,
        "source_profiles_basic_topology_valid": True,
        "new_revision_native_validation_required": True,
        "fabrication_suitable": False,
        "arbitrary_parameter_values_allowed": False,
    }:
        raise MutationError("Sphere metamorph profile policy is invalid")
    profiles = registry.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise MutationError("Sphere metamorph profile registry is empty")
    names: set[str] = set()
    for profile in profiles:
        if not isinstance(profile, dict):
            raise MutationError("Sphere metamorph profiles must be objects")
        name = profile.get("name")
        pars = profile.get("pars")
        evidence = profile.get("evidence")
        if not isinstance(name, str) or not name or name in names:
            raise MutationError("Sphere metamorph profile names must be unique")
        if (
            not isinstance(pars, list)
            or len(pars) != 12
            or any(
                not isinstance(token, str)
                or not token
                or any(character.isspace() for character in token)
                or not token.isascii()
                for token in pars
            )
        ):
            raise MutationError(f"Sphere metamorph profile {name!r} has invalid Pars")
        if (
            not isinstance(evidence, list)
            or not evidence
            or any(not isinstance(item, str) or not item for item in evidence)
        ):
            raise MutationError(f"Sphere metamorph profile {name!r} lacks evidence")
        names.add(name)
    return registry


def sphere_metamorph_profiles() -> tuple[str, ...]:
    """Return stable names of measured Sphere metamorph profiles."""

    return tuple(profile["name"] for profile in _sphere_profile_registry()["profiles"])


def sphere_metamorph_profile_evidence(name: str) -> tuple[str, ...]:
    """Return evidence identifiers for one measured profile."""

    return tuple(_sphere_profile(name)["evidence"])


def _sphere_profile(name: str) -> dict[str, Any]:
    for profile in _sphere_profile_registry()["profiles"]:
        if profile["name"] == name:
            return profile
    raise MutationError(f"unknown Sphere metamorph profile {name!r}")


@lru_cache(maxsize=1)
def _cylinder_profile_registry() -> dict[str, Any]:
    resource = files("xenodream_xxp").joinpath(
        "data", "xdx-1.220-cylinder-mutation-profiles.json"
    )
    registry = json.loads(resource.read_text(encoding="utf-8"))
    if registry.get("schema_version") != 1:
        raise MutationError("unsupported Cylinder metamorph profile schema")
    target = registry.get("target")
    if not isinstance(target, dict) or target != {
        "product": "XenoDream X",
        "format_version": "1.220",
        "operation": "Cylinder",
        "style": "13",
        "num_pars": 7,
    }:
        raise MutationError("Cylinder metamorph profile target is invalid")
    policy = registry.get("policy")
    if policy != {
        "replace_complete_parameter_vector": True,
        "source_profiles_native_evaluated": True,
        "source_profiles_basic_topology_valid": True,
        "new_revision_native_validation_required": True,
        "fabrication_suitable": False,
        "arbitrary_parameter_values_allowed": False,
    }:
        raise MutationError("Cylinder metamorph profile policy is invalid")
    profiles = registry.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise MutationError("Cylinder metamorph profile registry is empty")
    names: set[str] = set()
    for profile in profiles:
        if not isinstance(profile, dict):
            raise MutationError("Cylinder metamorph profiles must be objects")
        name = profile.get("name")
        pars = profile.get("pars")
        evidence = profile.get("evidence")
        if not isinstance(name, str) or not name or name in names:
            raise MutationError("Cylinder metamorph profile names must be unique")
        if (
            not isinstance(pars, list)
            or len(pars) != 7
            or any(
                not isinstance(token, str)
                or not token
                or any(character.isspace() for character in token)
                or not token.isascii()
                for token in pars
            )
        ):
            raise MutationError(
                f"Cylinder metamorph profile {name!r} has invalid Pars"
            )
        if (
            not isinstance(evidence, list)
            or not evidence
            or any(not isinstance(item, str) or not item for item in evidence)
        ):
            raise MutationError(
                f"Cylinder metamorph profile {name!r} lacks evidence"
            )
        names.add(name)
    return registry


def cylinder_metamorph_profiles() -> tuple[str, ...]:
    """Return stable names of measured Cylinder metamorph profiles."""

    return tuple(
        profile["name"] for profile in _cylinder_profile_registry()["profiles"]
    )


def cylinder_metamorph_profile_evidence(name: str) -> tuple[str, ...]:
    """Return evidence identifiers for one measured Cylinder profile."""

    return tuple(_cylinder_profile(name)["evidence"])


def _cylinder_profile(name: str) -> dict[str, Any]:
    for profile in _cylinder_profile_registry()["profiles"]:
        if profile["name"] == name:
            return profile
    raise MutationError(f"unknown Cylinder metamorph profile {name!r}")


def verified_operation_details(operation: VerifiedOperation) -> dict[str, object]:
    """Return the stable normalized description of one verified operation."""

    def vector(value: Vector3 | None) -> list[str] | None:
        return None if value is None else [str(value.x), str(value.y), str(value.z)]

    if isinstance(operation, ObjectMutation):
        return {
            "type": "object-mutation",
            "object_name": operation.object_name,
            "scale": vector(operation.scale),
            "rotation": vector(operation.rotation),
            "position": vector(operation.position),
            "color_density": None
            if operation.color_density is None
            else str(operation.color_density),
            "face_warp": None
            if operation.face_warp is None
            else str(operation.face_warp),
        }
    if isinstance(operation, CenteredRowMutation):
        return {
            "type": "centered-row",
            "spacing": str(operation.spacing),
            "center": vector(operation.center),
        }
    if isinstance(operation, SeededVariation):
        return {
            "type": "seeded-variation-v1",
            "seed": operation.seed,
            "strength": str(operation.strength),
        }
    if isinstance(operation, SphereMetamorphMutation):
        return {
            "type": "sphere-metamorph-profile-v1",
            "object_name": operation.object_name,
            "profile": operation.profile,
            "evidence": list(sphere_metamorph_profile_evidence(operation.profile)),
            "native_validation_required": True,
            "fabrication_suitable": False,
        }
    if isinstance(operation, CylinderMetamorphMutation):
        return {
            "type": "cylinder-metamorph-profile-v1",
            "object_name": operation.object_name,
            "profile": operation.profile,
            "evidence": list(cylinder_metamorph_profile_evidence(operation.profile)),
            "native_validation_required": True,
            "fabrication_suitable": False,
        }
    raise TypeError("unsupported verified operation")


def _matching_records(
    document: Document, section: bytes, key: bytes
) -> list[tuple[int, KeyValueRecord]]:
    return [
        (index, record)
        for index, record in enumerate(document.records)
        if isinstance(record, KeyValueRecord)
        and record.section == section
        and record.section_occurrence == 0
        and record.key == key
    ]


def _value(document: Document, section: bytes, key: bytes) -> bytes:
    matches = _matching_records(document, section, key)
    if len(matches) != 1:
        raise MutationError(
            f"expected one {section.decode('ascii', 'replace')}.{key.decode('ascii', 'replace')} record, "
            f"found {len(matches)}"
        )
    return matches[0][1].value


def _require_xdx_1220(document: Document) -> None:
    if _value(document, b"Header", b"Program") != b"XDX":
        raise MutationError("verified mutations require an XDX project")
    if _value(document, b"Header", b"Progversion") != b"1.220":
        raise MutationError("verified mutations require XDX version 1.220")


def _objects(
    document: Document,
    required: dict[str, tuple[SceneOperation, ...]] | None = None,
) -> tuple[_ObjectRecord, ...]:
    objects: list[_ObjectRecord] = []
    for node in sorted(
        _scene_nodes(document),
        key=lambda item: (
            item.holon_index,
            item.section_occurrence,
            item.ordinal,
        ),
    ):
        if node.holon_index <= 0 or node.type_code != 1:
            continue
        if node.name is None or node.constructor not in {"Cube", "Sphere"}:
            name = node.name or f"Holon\\{node.holon_index}"
            raise MutationError(
                f"{name} does not match a verified XDX 1.220 Cube or Sphere record"
            )
        kind = node.constructor.lower()
        missing = [
            operation.value
            for operation in (required or {}).get(kind, ())
            if operation not in node.allowed_operations
        ]
        if missing:
            raise MutationError(
                f"object {node.name!r} does not support {', '.join(missing)}"
            )
        objects.append(
            _ObjectRecord(
                f"Holon\\{node.holon_index}".encode("ascii"),
                node.name,
                kind,
            )
        )
    if not objects:
        raise MutationError("project contains no verified editable objects")
    return tuple(objects)


_UNBOUND_SCENE = SceneBinding("0" * 64, "0" * 64)


def _scene_nodes(document: Document) -> tuple[SceneNode, ...]:
    return _describe_document(document, _UNBOUND_SCENE).nodes


def _target_node(document: Document, object_name: str) -> SceneNode:
    matches = [
        node
        for node in _scene_nodes(document)
        if node.type_code == 1 and node.name == object_name
    ]
    if len(matches) != 1:
        raise MutationError(
            f"object name {object_name!r} matched {len(matches)} objects"
        )
    return matches[0]


def _target_object(node: SceneNode, object_name: str) -> _ObjectRecord:
    if node.constructor not in {"Cube", "Sphere"}:
        raise MutationError(
            f"{object_name} does not match a verified XDX 1.220 Cube or Sphere record"
        )
    return _ObjectRecord(
        f"Holon\\{node.holon_index}".encode("ascii"),
        object_name,
        node.constructor.lower(),
    )


def _require_object_capabilities(
    operation: ObjectMutation, node: SceneNode
) -> None:
    if node.constructor == "Sphere" and any(
        value is not None
        for value in (operation.rotation, operation.color_density, operation.face_warp)
    ):
        raise MutationError(
            "Sphere mutations support only scale and position until more fields are verified"
        )
    requested = {
        SceneOperation.SET_SCALE: operation.scale,
        SceneOperation.SET_ROTATION: operation.rotation,
        SceneOperation.SET_POSITION: operation.position,
        SceneOperation.SET_COLOR_DENSITY: operation.color_density,
        SceneOperation.SET_FACE_WARP: operation.face_warp,
    }
    missing = [
        capability.value
        for capability, value in requested.items()
        if value is not None and capability not in node.allowed_operations
    ]
    if missing:
        raise MutationError(
            f"object {operation.object_name!r} does not support {', '.join(missing)}"
        )


def _require_capability(
    node: SceneNode, object_name: str, capability: SceneOperation
) -> None:
    if capability not in node.allowed_operations:
        raise MutationError(
            f"object {object_name!r} does not support {capability.value}"
        )


def _format_decimal(value: Decimal, places: int, label: str) -> bytes:
    quantum = Decimal(1).scaleb(-places)
    try:
        quantized = value.quantize(quantum)
    except DecimalException as error:
        raise MutationError(f"{label} cannot be represented") from error
    if quantized != value:
        raise MutationError(f"{label} exceeds the verified {places}-place precision")
    return format(quantized, f".{places}f").encode("ascii")


def _replace_value(
    document: Document,
    section: bytes,
    key: bytes,
    value: Decimal,
    places: int,
    token_index: int | None,
) -> Document:
    replacement = _format_decimal(value, places, f"{section!r}.{key!r}")
    if token_index is None:
        return _replace_raw_value(document, section, key, replacement)
    return _replace_token(document, section, key, token_index, replacement)


def _replace_raw_value(
    document: Document, section: bytes, key: bytes, replacement: bytes
) -> Document:
    matches = _matching_records(document, section, key)
    if len(matches) != 1:
        raise MutationError(f"expected one editable {section!r}.{key!r} record")
    record_index, record = matches[0]
    separator = record.content.find(b"=")
    if separator < 0:
        raise MutationError("key/value record lost its separator")
    new_record = replace(
        record,
        content=record.content[: separator + 1] + replacement,
        value=replacement,
    )
    records = list(document.records)
    records[record_index] = new_record
    return Document(tuple(records))


def _replace_token(
    document: Document,
    section: bytes,
    key: bytes,
    token_index: int,
    replacement: bytes,
) -> Document:
    if not replacement or re.search(rb"\s", replacement):
        raise MutationError("replacement token must be one non-whitespace value")
    matches = _matching_records(document, section, key)
    if len(matches) != 1:
        raise MutationError(f"expected one editable {section!r}.{key!r} record")
    record = matches[0][1]
    tokens = list(re.finditer(rb"\S+", record.value))
    if token_index >= len(tokens):
        raise MutationError(f"missing token {token_index} in {section!r}.{key!r}")
    token = tokens[token_index]
    value = record.value[: token.start()] + replacement + record.value[token.end() :]
    return _replace_raw_value(document, section, key, value)


def _set_vector(
    document: Document, section: bytes, indices: tuple[int, int, int], value: Vector3
) -> Document:
    for token_index, component in zip(indices, (value.x, value.y, value.z)):
        document = _replace_value(
            document, section, b"Transform", component, 5, token_index
        )
    return document


def _decimal_token(
    document: Document, section: bytes, key: bytes, token_index: int
) -> Decimal:
    tokens = _value(document, section, key).split()
    if token_index >= len(tokens):
        raise MutationError(f"missing token {token_index} in {section!r}.{key!r}")
    try:
        value = Decimal(tokens[token_index].decode("ascii"))
    except (DecimalException, UnicodeDecodeError) as error:
        raise MutationError(
            f"{section!r}.{key!r} token {token_index} is not a decimal"
        ) from error
    if not value.is_finite():
        raise MutationError(f"{section!r}.{key!r} token {token_index} is not finite")
    return value


def _read_vector(
    document: Document, section: bytes, indices: tuple[int, int, int]
) -> Vector3:
    return Vector3(
        *(
            _decimal_token(document, section, b"Transform", token_index)
            for token_index in indices
        )
    )


def _quantized(value: Decimal, places: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN)


class _VariationSampler:
    def __init__(self, seed: int, strength: Decimal) -> None:
        self.random = random.Random(seed)
        self.strength = strength

    def _unit(self) -> Decimal:
        first = self.random.random() - self.random.random()
        second = self.random.random() - self.random.random()
        return Decimal(repr(first * second))

    def value(
        self,
        current: Decimal,
        amplitude: Decimal,
        preserve_probability: Decimal,
        *,
        minimum: Decimal | None = None,
        maximum: Decimal | None = None,
        places: int = 5,
    ) -> Decimal:
        if Decimal(repr(self.random.random())) < preserve_probability:
            return current
        value = current + self._unit() * amplitude * self.strength
        if minimum is not None:
            value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return _quantized(value, places)


def _apply_seeded_variation(
    document: Document,
    operation: SeededVariation,
    objects: tuple[_ObjectRecord, ...],
) -> tuple[Document, tuple[str, ...], set[_AllowedDifference]]:
    sampler = _VariationSampler(operation.seed, operation.strength)
    allowed: set[_AllowedDifference] = set()
    names: list[str] = []
    for obj in objects:
        field_count = 10 if obj.kind == "cube" else 6
        preserve_probability = min(
            Decimal("0.9"), Decimal("0.033") * max(0, field_count - 2)
        )
        scale = _read_vector(document, obj.section, (0, 1, 2))
        position = _read_vector(document, obj.section, (9, 10, 11))
        new_scale = Vector3(
            *(
                sampler.value(
                    component,
                    abs(component),
                    preserve_probability,
                    minimum=Decimal("0.01"),
                )
                for component in (scale.x, scale.y, scale.z)
            )
        )
        characteristic_size = max(
            Decimal("1"), abs(scale.x), abs(scale.y), abs(scale.z)
        )
        new_position = Vector3(
            *(
                sampler.value(component, characteristic_size, preserve_probability)
                for component in (position.x, position.y, position.z)
            )
        )
        if obj.kind == "cube":
            rotation = _read_vector(document, obj.section, (6, 7, 8))
            new_rotation = Vector3(
                *(
                    sampler.value(
                        component, Decimal("45"), preserve_probability
                    )
                    for component in (rotation.x, rotation.y, rotation.z)
                )
            )
            face_warp = _decimal_token(
                document, obj.section + b"\\MM\\0", b"Pars", 0
            )
            new_face_warp = sampler.value(
                face_warp,
                Decimal("0.25"),
                preserve_probability,
                minimum=Decimal("0"),
                maximum=Decimal("0.25"),
                places=4,
            )
            exact = ObjectMutation(
                obj.name,
                scale=new_scale,
                rotation=new_rotation,
                position=new_position,
                face_warp=new_face_warp,
            )
        else:
            exact = ObjectMutation(
                obj.name,
                scale=new_scale,
                position=new_position,
            )
        document, changed_names, changed_allowed = _apply_object_mutation(
            document, exact, objects
        )
        names.extend(changed_names)
        allowed.update(changed_allowed)
    return document, tuple(names), allowed


def _apply_object_mutation(
    document: Document, operation: ObjectMutation, objects: tuple[_ObjectRecord, ...]
) -> tuple[Document, tuple[str, ...], set[_AllowedDifference]]:
    matches = [item for item in objects if item.name == operation.object_name]
    if len(matches) != 1:
        raise MutationError(
            f"object name {operation.object_name!r} matched {len(matches)} objects"
        )
    obj = matches[0]
    if obj.kind == "sphere" and any(
        value is not None
        for value in (operation.rotation, operation.color_density, operation.face_warp)
    ):
        raise MutationError(
            "Sphere mutations support only scale and position until more fields are verified"
        )

    allowed: set[_AllowedDifference] = set()
    if operation.scale is not None:
        document = _set_vector(document, obj.section, (0, 1, 2), operation.scale)
        allowed.update(
            _allowed_difference(obj.section, "Transform", index)
            for index in (0, 1, 2)
        )
    if operation.rotation is not None:
        document = _set_vector(document, obj.section, (6, 7, 8), operation.rotation)
        allowed.update(
            _allowed_difference(obj.section, "Transform", index)
            for index in (6, 7, 8)
        )
    if operation.position is not None:
        document = _set_vector(document, obj.section, (9, 10, 11), operation.position)
        allowed.update(
            _allowed_difference(obj.section, "Transform", index)
            for index in (9, 10, 11)
        )
    if operation.color_density is not None:
        document = _replace_value(
            document, obj.section, b"GradDensity", operation.color_density, 3, None
        )
        allowed.add(_allowed_difference(obj.section, "GradDensity", None))
    if operation.face_warp is not None:
        metamorph = obj.section + b"\\MM\\0"
        document = _replace_value(
            document, metamorph, b"Pars", operation.face_warp, 4, 0
        )
        allowed.add(_allowed_difference(metamorph, "Pars", 0))
    return document, (obj.name,), allowed


def _apply_sphere_metamorph_mutation(
    document: Document,
    operation: SphereMetamorphMutation,
    objects: tuple[_ObjectRecord, ...],
) -> tuple[Document, tuple[str, ...], set[_AllowedDifference]]:
    matches = [item for item in objects if item.name == operation.object_name]
    if len(matches) != 1:
        raise MutationError(
            f"object name {operation.object_name!r} matched {len(matches)} objects"
        )
    obj = matches[0]
    if obj.kind != "sphere":
        raise MutationError("Sphere metamorph profiles require a verified Sphere")
    metamorph = obj.section + b"\\MM\\0"
    if _value(document, metamorph, b"Style") != b"1":
        raise MutationError("Sphere metamorph profile requires Style 1")
    if _value(document, metamorph, b"NumPars") != b"12":
        raise MutationError("Sphere metamorph profile requires NumPars 12")
    if len(_value(document, metamorph, b"Pars").split()) != 12:
        raise MutationError("Sphere metamorph profile requires twelve Pars tokens")

    profile = _sphere_profile(operation.profile)
    for token_index, token in enumerate(profile["pars"]):
        document = _replace_token(
            document,
            metamorph,
            b"Pars",
            token_index,
            token.encode("ascii"),
        )
    allowed = {
        _allowed_difference(metamorph, "Pars", token_index)
        for token_index in range(12)
    }
    return document, (obj.name,), allowed


def _cylinder_object(
    document: Document, object_name: str
) -> _ObjectRecord:
    node = _target_node(document, object_name)
    return _ObjectRecord(
        f"Holon\\{node.holon_index}".encode("ascii"), object_name, "cylinder"
    )


def _apply_cylinder_metamorph_mutation(
    document: Document,
    operation: CylinderMetamorphMutation,
) -> tuple[Document, tuple[str, ...], set[_AllowedDifference]]:
    obj = _cylinder_object(document, operation.object_name)
    metamorph = obj.section + b"\\MM\\0"
    if _value(document, metamorph, b"Style") != b"13":
        raise MutationError("Cylinder metamorph profile requires Style 13")
    if _value(document, metamorph, b"NumPars") != b"7":
        raise MutationError("Cylinder metamorph profile requires NumPars 7")
    if len(_value(document, metamorph, b"Pars").split()) != 7:
        raise MutationError("Cylinder metamorph profile requires seven Pars tokens")

    profile = _cylinder_profile(operation.profile)
    for token_index, token in enumerate(profile["pars"]):
        document = _replace_token(
            document,
            metamorph,
            b"Pars",
            token_index,
            token.encode("ascii"),
        )
    allowed = {
        _allowed_difference(metamorph, "Pars", token_index)
        for token_index in range(7)
    }
    return document, (obj.name,), allowed


def _apply_row_mutation(
    document: Document,
    operation: CenteredRowMutation,
    objects: tuple[_ObjectRecord, ...],
) -> tuple[Document, tuple[str, ...], set[_AllowedDifference]]:
    signature = tuple(item.kind for item in objects)
    if signature not in _SUPPORTED_SIGNATURES:
        raise MutationError("row mutation requires a currently supported object sequence")
    start = operation.center.x - operation.spacing * Decimal(len(objects) - 1) / 2
    allowed: set[_AllowedDifference] = set()
    for index, obj in enumerate(objects):
        position = Vector3(
            start + operation.spacing * index,
            operation.center.y,
            operation.center.z,
        )
        document = _set_vector(document, obj.section, (9, 10, 11), position)
        allowed.update(
            _allowed_difference(obj.section, "Transform", token)
            for token in (9, 10, 11)
        )
    return document, tuple(item.name for item in objects), allowed


def apply_verified_mutation(data: bytes, operation: VerifiedOperation) -> MutationResult:
    """Apply one verified operation while preserving every unrelated byte."""

    if not isinstance(
        operation,
        (
            ObjectMutation,
            CenteredRowMutation,
            SeededVariation,
            SphereMetamorphMutation,
            CylinderMetamorphMutation,
        ),
    ):
        raise TypeError(
            "operation must be ObjectMutation, CenteredRowMutation, "
            "SeededVariation, SphereMetamorphMutation, or "
            "CylinderMetamorphMutation"
        )
    original = parse_bytes(data)
    if original.to_bytes() != data:
        raise MutationError("input failed exact parser round trip")
    _require_xdx_1220(original)
    if isinstance(operation, CylinderMetamorphMutation):
        node = _target_node(original, operation.object_name)
        _require_capability(
            node,
            operation.object_name,
            SceneOperation.APPLY_CYLINDER_PROFILE,
        )
        mutated, names, allowed = _apply_cylinder_metamorph_mutation(
            original, operation
        )
    else:
        if isinstance(operation, ObjectMutation):
            node = _target_node(original, operation.object_name)
            obj = _target_object(node, operation.object_name)
            _require_object_capabilities(operation, node)
            mutated, names, allowed = _apply_object_mutation(
                original, operation, (obj,)
            )
        elif isinstance(operation, CenteredRowMutation):
            objects = _objects(
                original,
                {
                    "cube": (SceneOperation.SET_POSITION,),
                    "sphere": (SceneOperation.SET_POSITION,),
                },
            )
            mutated, names, allowed = _apply_row_mutation(
                original, operation, objects
            )
        elif isinstance(operation, SphereMetamorphMutation):
            node = _target_node(original, operation.object_name)
            obj = _target_object(node, operation.object_name)
            _require_capability(
                node,
                operation.object_name,
                SceneOperation.APPLY_SPHERE_PROFILE,
            )
            mutated, names, allowed = _apply_sphere_metamorph_mutation(
                original, operation, (obj,)
            )
        else:
            objects = _objects(
                original,
                {
                    "cube": (
                        SceneOperation.SET_SCALE,
                        SceneOperation.SET_ROTATION,
                        SceneOperation.SET_POSITION,
                        SceneOperation.SET_FACE_WARP,
                    ),
                    "sphere": (
                        SceneOperation.SET_SCALE,
                        SceneOperation.SET_POSITION,
                    ),
                },
            )
            mutated, names, allowed = _apply_seeded_variation(
                original, operation, objects
            )

    differences = tuple(diff_documents(original, mutated))
    unexpected = []
    for item in differences:
        locator = (
            item.get("section"),
            item.get("section_occurrence"),
            item.get("key"),
            item.get("key_occurrence"),
            item.get("token_index"),
        )
        if locator not in allowed:
            unexpected.append(item)
    if unexpected:
        raise MutationError(f"mutation changed unsupported fields: {unexpected}")
    output = mutated.to_bytes()
    if parse_bytes(output).to_bytes() != output:
        raise MutationError("mutated output failed exact parser round trip")
    return MutationResult(
        output,
        output != data,
        differences,
        names,
        native_validation_required=isinstance(
            operation, (SphereMetamorphMutation, CylinderMetamorphMutation)
        ),
        fabrication_suitable=False,
    )
