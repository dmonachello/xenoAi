"""Natural-language creation constrained by verified XenoDream operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import os
from pathlib import Path
import re
import shutil
from uuid import uuid4

from .adapter import XenoDreamArtifactAdapter
from .generator import (
    ClosedConstructorName,
    ClosedConstructorSpec,
    compile_closed_constructor,
    compile_cube,
    compile_cylinder,
    compile_sphere,
)
from .planning import (
    HeadBinding,
    MutationPlan,
    OperationSequencePlan,
    PlannerIdentity,
    WorkspacePlan,
    plan_request,
    workspace_plan_to_dict,
)
from .scene import SceneBinding, SceneDescription, describe_xdx_scene
from .workspace import ProjectWorkspace


class CreationError(ValueError):
    """A natural-language creation request cannot be admitted safely."""


class CreationSeed(StrEnum):
    CUBE = "Cube"
    SPHERE = "Sphere"
    CYLINDER = "Cylinder"
    ROUND_CUBE = "RoundCube"
    PIPE = "Pipe"
    TORUS = "Torus"
    COG = "Cog"
    SPIRAL_SHELL = "SpiralShell"


@dataclass(frozen=True, slots=True)
class CreationRecipe:
    seed: CreationSeed
    recipe: str
    summary: str
    unsupported: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.seed, CreationSeed):
            raise TypeError("seed must be CreationSeed")
        if not isinstance(self.recipe, str):
            raise TypeError("recipe must be text")
        if len(self.recipe) > 1500:
            raise CreationError("recipe exceeds the 1500-character limit")
        if "\n" in self.recipe or "\r" in self.recipe:
            raise CreationError("recipe must be one line")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise CreationError("summary must be non-empty text")
        if len(self.summary) > 500:
            raise CreationError("summary exceeds the 500-character limit")
        if not isinstance(self.unsupported, tuple) or any(
            not isinstance(item, str) or not item.strip() for item in self.unsupported
        ):
            raise CreationError("unsupported must contain non-empty text values")
        if len(self.unsupported) > 12:
            raise CreationError("unsupported cannot contain more than 12 items")


@dataclass(frozen=True, slots=True)
class ModelCreation:
    recipe: CreationRecipe
    model: str
    response_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.recipe, CreationRecipe):
            raise TypeError("recipe must be CreationRecipe")
        if not isinstance(self.model, str) or re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", self.model
        ) is None:
            raise CreationError("model must be a supported ASCII identifier")
        if not isinstance(self.response_id, str) or re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_-]{0,255}", self.response_id
        ) is None:
            raise CreationError("response ID must be a supported ASCII identifier")


@dataclass(frozen=True, slots=True)
class CreationPreview:
    creation: ModelCreation
    plan: WorkspacePlan | None
    seed_sha256: str
    output_sha256: str
    output_data: bytes
    scene: SceneDescription
    operations: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class CreationResult:
    preview: CreationPreview
    workspace: str
    revision_id: str
    export: str | None


def _seed_bytes(seed: CreationSeed) -> bytes:
    if seed is CreationSeed.CUBE:
        return compile_cube()
    if seed is CreationSeed.SPHERE:
        return compile_sphere()
    if seed is CreationSeed.CYLINDER:
        return compile_cylinder()
    return compile_closed_constructor(
        ClosedConstructorSpec(ClosedConstructorName(seed.value))
    )


def _provider_plan(plan: WorkspacePlan, prompt: str, model: str) -> WorkspacePlan:
    planner = PlannerIdentity("openai-responses", model)
    if isinstance(plan, MutationPlan):
        return MutationPlan(prompt, plan.rule, plan.base, plan.operation, planner)
    return OperationSequencePlan(prompt, plan.base, plan.steps, planner)


def _evaluate(data: bytes, plan: WorkspacePlan | None) -> bytes:
    if plan is None:
        return data
    adapter = XenoDreamArtifactAdapter()
    if isinstance(plan, MutationPlan):
        return adapter.apply(data, plan.operation).data
    for step in plan.steps:
        data = adapter.apply(data, step.operation).data
    return data


def _operation_dicts(plan: WorkspacePlan | None) -> tuple[dict[str, object], ...]:
    if plan is None:
        return ()
    value = workspace_plan_to_dict(plan)
    if isinstance(plan, MutationPlan):
        return (dict(value["operation"]),)
    return tuple(dict(step["operation"]) for step in value["steps"])


def preview_creation(prompt: str, creation: ModelCreation) -> CreationPreview:
    """Compile and fully evaluate a model recipe without durable writes."""

    if not isinstance(prompt, str) or not prompt.strip():
        raise CreationError("prompt must be non-empty text")
    if len(prompt) > 20_000:
        raise CreationError("prompt exceeds the 20000-character limit")
    if not isinstance(creation, ModelCreation):
        raise TypeError("creation must be ModelCreation")
    if creation.recipe.unsupported:
        raise CreationError(
            "request includes unsupported intent: "
            + "; ".join(creation.recipe.unsupported)
        )
    seed_data = _seed_bytes(creation.recipe.seed)
    seed_sha = sha256(seed_data).hexdigest()
    plan: WorkspacePlan | None = None
    try:
        if creation.recipe.recipe.strip():
            parsed = plan_request(
                creation.recipe.recipe,
                base=HeadBinding("0" * 64, seed_sha),
            )
            plan = _provider_plan(parsed, prompt.strip(), creation.model)
        output = _evaluate(seed_data, plan)
        output_sha = sha256(output).hexdigest()
        scene = describe_xdx_scene(output, SceneBinding("preview", output_sha))
    except (TypeError, ValueError) as error:
        raise CreationError(f"translated recipe is not executable: {error}") from error
    return CreationPreview(
        creation,
        plan,
        seed_sha,
        output_sha,
        output,
        scene,
        _operation_dicts(plan),
    )


def apply_creation(
    workspace: str | Path,
    *,
    prompt: str,
    creation: ModelCreation,
    message: str,
    export: str | Path | None = None,
) -> CreationResult:
    """Publish a completely evaluated creation as one new workspace."""

    target = Path(workspace).resolve()
    export_path = None if export is None else Path(export).resolve()
    if target.exists():
        raise CreationError(f"refusing to overwrite workspace: {target}")
    if export_path is not None and export_path.exists():
        raise CreationError(f"refusing to overwrite export: {export_path}")
    if not isinstance(message, str) or not message.strip():
        raise CreationError("message must be non-empty text")
    preview = preview_creation(prompt, creation)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{target.name}.create-{uuid4().hex}"
    provenance = {
        "schema": "xenosculpt-natural-creation/v1",
        "provider": "openai-responses",
        "model": creation.model,
        "response_id": creation.response_id,
        "seed": creation.recipe.seed.value,
        "recipe": creation.recipe.recipe,
        "summary": creation.recipe.summary,
        "seed_sha256": preview.seed_sha256,
    }
    try:
        project = ProjectWorkspace.create_from_bytes(
            staging,
            _seed_bytes(creation.recipe.seed),
            source_label=f"generated:{creation.recipe.seed.value}",
            initial_details={"creation": provenance},
            initial_message=message,
            initial_prompt=prompt.strip(),
        )
        if creation.recipe.recipe.strip():
            parsed = plan_request(
                creation.recipe.recipe,
                base=HeadBinding.from_revision(project.status().head),
            )
            project.apply_plan(
                _provider_plan(parsed, prompt.strip(), creation.model),
                message=message,
            )
        status = project.status()
        if status.head.artifact_sha256 != preview.output_sha256:
            raise CreationError("staged workspace does not match the verified preview")
        os.replace(staging, target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    published = ProjectWorkspace.open(target)
    artifact = None if export_path is None else published.export(export_path)
    return CreationResult(
        preview,
        str(target),
        published.status().head.id,
        None if artifact is None else artifact.path,
    )
