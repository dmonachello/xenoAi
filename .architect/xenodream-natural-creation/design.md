# XenoDream natural-language creation

## Decision

Implement Candidate A. A hosted OpenAI model translates free-form intent into
a strict seed-and-recipe document. It has no byte, filesystem, workspace, or
native-application tools. XenoSculpt remains the authority for compilation,
operation parsing, capability checks, mutation, revision creation, and export.

## Public contract

```powershell
xenosculpt create WORKSPACE --prompt TEXT --model MODEL_ID [--export FILE] [--dry-run]
```

`OPENAI_API_KEY` is read from the environment. `--dry-run` performs the model
request and complete in-memory evaluation but writes no workspace or export.
Without it, the command refuses an existing workspace/export, builds in a
sibling staging directory, verifies the staged artifact hash against preview,
and atomically publishes the workspace. Export uses the normal non-overwriting
workspace export path.

The model response is strict JSON:

```json
{
  "seed": "Cube",
  "recipe": "add Sphere at 55 0 0; apply Sphere profile cushion-core to object Sphere3",
  "summary": "A cube and cushioned sphere composition.",
  "unsupported": []
}
```

An empty recipe is allowed for a seed-only project. A non-empty `unsupported`
array makes the command fail closed. Recipes use one operation or two through
five semicolon-separated operations, matching the existing grammar exactly.

## Types and ownership

```python
class CreationSeed(StrEnum): ...

@dataclass(frozen=True)
class CreationRecipe:
    seed: CreationSeed
    recipe: str
    summary: str
    unsupported: tuple[str, ...]

@dataclass(frozen=True)
class ModelCreation:
    recipe: CreationRecipe
    model: str
    response_id: str

@dataclass(frozen=True)
class CreationPreview:
    creation: ModelCreation
    plan: WorkspacePlan | None
    seed_sha256: str
    output_sha256: str
    scene: SceneDescription
```

`openai_planner.py` is the only HTTP/provider module. `creation.py` is the
XenoDream application service. Existing `planning.py`, `mutation.py`, and
`workspace.py` remain the deterministic execution path. Core learns nothing
about prompts, scenes, or OpenAI.

## Provenance

The initial revision stores the original prompt, model, provider response ID,
seed, translated recipe, and seed hash. Applied plans use planner identity
`openai-responses/<model>` and retain the original prompt while persisting the
same verified operation details already used for deterministic recipes.
Default arguments preserve all existing revision IDs and schemas.

## Verification sequence

1. Strict response decoding, duplicate-key rejection, response-size bound, and
   missing-key/error tests.
2. Every seed compiles and describes; representative Cube/Sphere and closed
   constructor recipes evaluate in memory.
3. Unsupported intent, invalid recipes, stale plans, existing destinations,
   and mid-stage failures publish nothing.
4. Dry-run changes no filesystem state.
5. Applied workspace hash equals preview; exported XDX equals HEAD artifact.
6. Full suite, reference verifier, package build/help/smoke, then existing
   ComfyUI and MoI regression checks.

## Rejected shortcuts

- No model-generated XDX, JSON Patch, arbitrary Python, or shell commands.
- No automatic native validation or fabrication claim.
- No provider key on the command line or in revision metadata.
- No generic provider framework in core before a second provider proves it.
- No model tool loop or partial workspace publication in this milestone.

## Red-flag audit

The HTTP wrapper and creation service each own a real policy boundary rather
than forwarding arguments. Existing mutation and revision layers are reused,
not duplicated. Provider response decoding is separate from domain admission.
Creation is one staged transaction from the caller's perspective. The design
adds no universal scene abstraction and exposes no speculative extension API.
