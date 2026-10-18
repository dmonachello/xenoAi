# Natural-language XenoDream creation

`xenosculpt create` turns a broader text request into a new revision workspace
and, optionally, an editable `.xxp` export. It uses the OpenAI Responses API as
a translator. XenoSculpt remains the execution authority.

## Preview a request

```powershell
xenosculpt auth login
xenosculpt auth models

./dist/xenosculpt.exe create ./output/sculpture.xsp `
  --prompt "Make a broad cube with a cushioned sphere 55 units to its right" `
  --model MODEL_FROM_AUTH_MODELS `
  --export ./output/sculpture.xxp `
  --dry-run
```

The result includes the selected seed, exact controlled recipe, typed
operations, artifact hashes, complete scene description, and any unsupported
parts. The dry run writes no workspace or export, but it does make a hosted API
request. A later invocation is a new request and may translate the prompt
differently.

## Create the workspace and native file

Run the same command without `--dry-run`:

```powershell
./dist/xenosculpt.exe create ./output/sculpture.xsp `
  --prompt "Make a broad cube with a cushioned sphere 55 units to its right" `
  --model MODEL_FROM_AUTH_MODELS `
  --export ./output/sculpture.xxp
```

The command refuses to overwrite either destination. It compiles the seed,
parses the recipe through the controlled grammar, evaluates every operation in
memory, builds a sibling staging workspace, and verifies the staged HEAD hash
against the preview before publication. The exported `.xxp` is the exact HEAD
artifact and can be opened manually in XenoDream.

The initial revision records the original prompt, provider, model, response ID,
seed, recipe, summary, usage source, and seed hash. Recipe revisions record the same typed
operation provenance as `project prompt`.

ChatGPT-plan credentials are the default. API-key billing remains available
with `OPENAI_API_KEY` plus `--auth api-key`. XenoSculpt never silently switches
between the two billing sources. See [ChatGPT-plan authentication](chatgpt-plan-auth.md).

## Supported vocabulary

Seeds are Cube, Sphere, Cylinder, RoundCube, Pipe, Torus, Cog, SpiralShell, and
the fixed `InteractingSpirals` composition. The latter contains eight named
members in the native-validated `interleaved-eight/v1` profile; it is not an
arbitrary spiral grammar. See
[Interacting XenoDream spirals](xenodream-interacting-spirals.md).
Recipes may use verified absolute transforms, Cube measured fields, admitted
Cube or Sphere additions, centered rows, seeded variation, and measured Sphere
or Cylinder profiles. A recipe contains at most five operations.

The command rejects a request when the model reports unsupported intent or the
recipe fails deterministic parsing or mutation admission. It does not
approximate unsupported features.

## Security and evidence boundary

- The prompt is sent to the OpenAI Responses API.
- ChatGPT-plan tokens use the protected account store; explicitly selected API
  keys are read from `OPENAI_API_KEY` and are never persisted.
- The selected model is explicit and recorded.
- The response uses strict JSON Schema and a bounded body.
- The model cannot emit XDX bytes, run code, access files, or control XenoDream.
- No creation result claims native validity or fabrication suitability.

Run `project validate --profile preview` or `review` separately when native
evaluation is required.
