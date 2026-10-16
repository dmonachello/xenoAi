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
from .document import Document, KeyValueRecord, SectionRecord, parse_bytes
from .generator import Vector3


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


VerifiedOperation: TypeAlias = (
    ObjectMutation | CenteredRowMutation | SeededVariation | SphereMetamorphMutation
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


_HOLON_SECTION = re.compile(rb"Holon\\([0-9]+)$")
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


def _objects(document: Document) -> tuple[_ObjectRecord, ...]:
    indexed_sections: list[tuple[int, bytes]] = []
    for record in document.records:
        if not isinstance(record, SectionRecord) or record.occurrence != 0:
            continue
        match = _HOLON_SECTION.fullmatch(record.name)
        if match and int(match.group(1)) > 0:
            indexed_sections.append((int(match.group(1)), record.name))

    objects: list[_ObjectRecord] = []
    for _, section in sorted(indexed_sections):
        if _value(document, section, b"Type") != b"1":
            continue
        try:
            name = _value(document, section, b"Name").decode("ascii")
        except UnicodeDecodeError as error:
            raise MutationError("verified object names must be ASCII") from error
        metamorph = section + b"\\MM\\0"
        style = _value(document, metamorph, b"Style")
        num_pars = _value(document, metamorph, b"NumPars")
        pars = _value(document, metamorph, b"Pars")
        if style == b"5" and num_pars == b"9" and len(pars.split()) == 9:
            kind = "cube"
        elif style == b"1" and num_pars == b"12" and len(pars.split()) == 12:
            kind = "sphere"
        else:
            raise MutationError(
                f"{name} does not match a verified XDX 1.220 Cube or Sphere record"
            )
        objects.append(_ObjectRecord(section, name, kind))
    if not objects:
        raise MutationError("project contains no verified editable objects")
    return tuple(objects)


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
) -> tuple[Document, tuple[str, ...], set[tuple[str, str, int | None]]]:
    sampler = _VariationSampler(operation.seed, operation.strength)
    allowed: set[tuple[str, str, int | None]] = set()
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
) -> tuple[Document, tuple[str, ...], set[tuple[str, str, int | None]]]:
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

    allowed: set[tuple[str, str, int | None]] = set()
    if operation.scale is not None:
        document = _set_vector(document, obj.section, (0, 1, 2), operation.scale)
        allowed.update((obj.section.decode(), "Transform", index) for index in (0, 1, 2))
    if operation.rotation is not None:
        document = _set_vector(document, obj.section, (6, 7, 8), operation.rotation)
        allowed.update((obj.section.decode(), "Transform", index) for index in (6, 7, 8))
    if operation.position is not None:
        document = _set_vector(document, obj.section, (9, 10, 11), operation.position)
        allowed.update((obj.section.decode(), "Transform", index) for index in (9, 10, 11))
    if operation.color_density is not None:
        document = _replace_value(
            document, obj.section, b"GradDensity", operation.color_density, 3, None
        )
        allowed.add((obj.section.decode(), "GradDensity", None))
    if operation.face_warp is not None:
        metamorph = obj.section + b"\\MM\\0"
        document = _replace_value(
            document, metamorph, b"Pars", operation.face_warp, 4, 0
        )
        allowed.add((metamorph.decode(), "Pars", 0))
    return document, (obj.name,), allowed


def _apply_sphere_metamorph_mutation(
    document: Document,
    operation: SphereMetamorphMutation,
    objects: tuple[_ObjectRecord, ...],
) -> tuple[Document, tuple[str, ...], set[tuple[str, str, int | None]]]:
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
        (metamorph.decode(), "Pars", token_index) for token_index in range(12)
    }
    return document, (obj.name,), allowed


def _apply_row_mutation(
    document: Document,
    operation: CenteredRowMutation,
    objects: tuple[_ObjectRecord, ...],
) -> tuple[Document, tuple[str, ...], set[tuple[str, str, int | None]]]:
    signature = tuple(item.kind for item in objects)
    if signature not in _SUPPORTED_SIGNATURES:
        raise MutationError("row mutation requires a currently supported object sequence")
    start = operation.center.x - operation.spacing * Decimal(len(objects) - 1) / 2
    allowed: set[tuple[str, str, int | None]] = set()
    for index, obj in enumerate(objects):
        position = Vector3(
            start + operation.spacing * index,
            operation.center.y,
            operation.center.z,
        )
        document = _set_vector(document, obj.section, (9, 10, 11), position)
        allowed.update((obj.section.decode(), "Transform", token) for token in (9, 10, 11))
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
        ),
    ):
        raise TypeError(
            "operation must be ObjectMutation, CenteredRowMutation, "
            "SeededVariation, or SphereMetamorphMutation"
        )
    original = parse_bytes(data)
    if original.to_bytes() != data:
        raise MutationError("input failed exact parser round trip")
    _require_xdx_1220(original)
    objects = _objects(original)
    if isinstance(operation, ObjectMutation):
        mutated, names, allowed = _apply_object_mutation(original, operation, objects)
    elif isinstance(operation, CenteredRowMutation):
        mutated, names, allowed = _apply_row_mutation(original, operation, objects)
    elif isinstance(operation, SphereMetamorphMutation):
        mutated, names, allowed = _apply_sphere_metamorph_mutation(
            original, operation, objects
        )
    else:
        mutated, names, allowed = _apply_seeded_variation(
            original, operation, objects
        )

    differences = tuple(diff_documents(original, mutated))
    unexpected = []
    for item in differences:
        locator = (
            item.get("section"),
            item.get("key"),
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
        native_validation_required=isinstance(operation, SphereMetamorphMutation),
        fabrication_suitable=False,
    )
