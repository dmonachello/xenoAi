# M22: revise and run ComfyUI API workflows

## Problem

M22 must prove that the M21 revision core works for an application unlike XenoDream. ComfyUI saves two JSON forms with different jobs. The frontend workflow preserves layout and groups. The API workflow is the graph submitted to the server. M22 uses API-format JSON as its revision artifact because execution is the feature under test. It does not claim to preserve or derive the editable frontend workflow.

The installed target is ComfyUI 0.3.45 at commit `9a470e0`. Its server accepts API workflows through `POST /prompt`, exposes terminal records through `GET /history/{prompt_id}`, and returns output files through `GET /view`.

## Usage

Export a workflow through ComfyUI's API-format command, then create a workspace:

```powershell
xenosculpt comfyui init portrait.csp portrait-api.json
```

Change one existing input while ComfyUI is stopped:

```powershell
xenosculpt comfyui set-input portrait.csp 6 text `
  --value-json '"a ceramic owl under soft studio light"' `
  --message "change positive prompt"
```

Set a connection explicitly:

```powershell
xenosculpt comfyui set-input portrait.csp 8 images `
  --link-node 7 --link-output 0 `
  --message "route node 7 output 0"
```

Run the current revision against a local ComfyUI server:

```powershell
xenosculpt comfyui run portrait.csp `
  --server http://127.0.0.1:8188 `
  --timeout-seconds 600
```

The command records the run before network I/O. If the wait expires, use the same durable prompt ID without submitting again:

```powershell
xenosculpt comfyui resume portrait.csp RUN_ID --timeout-seconds 600
```

Revision commands remain available offline:

```powershell
xenosculpt comfyui status portrait.csp
xenosculpt comfyui log portrait.csp
xenosculpt comfyui compare portrait.csp main alternate
xenosculpt comfyui export portrait.csp portrait-revised-api.json
```

The existing XenoDream commands do not change.

## Shape

### API workflow document

`xenosculpt.comfyui.workflow` owns strict JSON decoding, API-format admission, typed input edits, canonical serialization, and semantic comparison.

```python
JsonValue = None | bool | int | float | str | tuple["JsonValue", ...] | JsonObject

@dataclass(frozen=True, slots=True)
class NodeId:
    value: str

@dataclass(frozen=True, slots=True)
class LiteralInput:
    value: JsonValue

@dataclass(frozen=True, slots=True)
class NodeLink:
    source: NodeId
    output_index: int

@dataclass(frozen=True, slots=True)
class SetNodeInput:
    node_id: NodeId
    input_name: str
    value: LiteralInput | NodeLink

class ApiWorkflow:
    @classmethod
    def parse(cls, data: bytes) -> ApiWorkflow: ...
    def canonical_bytes(self) -> bytes: ...
    def set_input(self, operation: SetNodeInput) -> WorkflowChange: ...
    def differences(self, other: ApiWorkflow) -> tuple[WorkflowDifference, ...]: ...
```

The parser accepts UTF-8 JSON only. It rejects duplicate object keys, non-finite numbers, an empty graph, nonnumeric node IDs, missing `class_type`, and non-object `inputs`. It diagnoses frontend workflow JSON separately and tells the user to export API format. It verifies that every parsed link references an existing node.

`SetNodeInput` requires an existing node and input. The operation separates literal values from `NodeLink`, so a CLI caller cannot create a connection by accident. Unknown node members and custom-node input values remain intact.

Imported workflows become canonical UTF-8 JSON with sorted keys, compact separators, and a trailing newline. The workspace stores both the source-file hash and the canonical artifact hash. Complete JSON Pointer differences describe semantic changes without relying on whitespace.

### ComfyUI workspace

```python
COMFYUI_APPLICATION = ApplicationIdentity(
    name="comfyui",
    document_kind="comfyui/api-workflow/v1",
    artifact_suffix=".json",
)

class ComfyProject(RevisionWorkspace):
    @classmethod
    def create(cls, root: PathLike, source: PathLike) -> ComfyProject: ...
    @classmethod
    def open(cls, root: PathLike) -> ComfyProject: ...
    def status(self) -> ComfyProjectStatus: ...
    def set_input(self, operation: SetNodeInput, *, message: str) -> WorkflowEditResult: ...
    def compare(self, before: str, after: str) -> tuple[WorkflowDifference, ...]: ...
    def run(self, *, ref: str, endpoint: ComfyEndpoint, wait: WaitPolicy) -> ComfyRun: ...
    def resume(self, run_id: UUID, *, wait: WaitPolicy) -> ComfyRun: ...
    def run_status(self, run_id: UUID) -> ComfyRun: ...
```

The workspace uses the shared metadata, revision, branch, and state tables. It adds ComfyUI-owned run and output tables. The core gains no generic execution model.

`set_input()` parses the selected artifact, applies one typed change, and commits through `_record_revision()` with the expected parent. A no-op does not advance `HEAD`. Revision details identify the node, input, class type, and before and after values.

### Durable execution

```python
class RunState(StrEnum):
    PREPARED = "prepared"
    SUBMISSION_UNKNOWN = "submission_unknown"
    SUBMITTED = "submitted"
    OUTPUT_INCOMPLETE = "output_incomplete"
    SUCCEEDED = "succeeded"
    REJECTED = "rejected"
    FAILED = "failed"

@dataclass(frozen=True, slots=True)
class ComfyRun:
    id: UUID
    revision_id: str
    artifact_sha256: str
    prompt_id: UUID
    server_origin: str
    state: RunState
    comfyui_version: str | None
    outputs: tuple[ComfyOutput, ...]
    error: dict[str, JsonValue] | None
```

`run()` stores `PREPARED` with the exact request bytes and revision identity before it calls the server. A valid receipt moves the run to `SUBMITTED`. A connection failure after sending moves it to `SUBMISSION_UNKNOWN`; the client never retries the POST. ComfyUI 0.3.45 accepts caller-selected prompt IDs without a uniqueness check, so retrying could execute the graph twice.

`resume()` only polls history. A successful terminal history record triggers output download and content-addressed storage. M22 retains PNG, JPEG, and WebP files reported under `outputs.<node>.images`. Unsupported or failed downloads produce `OUTPUT_INCOMPLETE`, not success. The run records distinct hashes for the submitted graph and ComfyUI's accepted graph because validation may normalize values. Runs never move workspace `HEAD`.

The server boundary accepts loopback HTTP by default. Remote servers require `--allow-remote`. The client rejects redirects, caps JSON and output sizes, uses fixed routes, checks that the returned prompt ID matches the submitted ID, and never joins a server filename to a local path. Output suffixes come from file signatures.

The run records `/system_stats` and the reported ComfyUI version. Version 0.3.45 is the tested target. A mismatch blocks submission unless the user passes `--allow-version-mismatch`. Model hashes, custom-node commits, and input assets are not captured yet, so a successful run is evidence of execution, not full environment reproducibility.

### CLI composition

`xenosculpt.cli` dispatches the first `comfyui` token to `xenosculpt.comfyui.cli`. Every other argument list goes unchanged to `xenodream_xxp.cli.main`. Both the packaged `xenosculpt.exe` and the installed `xenosculpt` command use the dispatcher. The historical `xxp` command remains available.

```text
src/xenosculpt/
  cli.py
  core/
  comfyui/
    cli.py
    client.py
    workflow.py
    workspace.py
```

## Synthesis decision

The execution-focused candidate is the base because a real second application should test both revision reuse and a different execution model. The offline candidate supplied strict document admission and complete semantic comparison. The paired-document candidate supplied the model-free `EmptyImage -> SaveImage` live proof.

M22 does not store the frontend workflow. Requiring both JSON forms would preserve more editor state, but XenoSculpt cannot verify that an arbitrary pair came from one editor state. An atomic pair would look stronger than the evidence allows. A later milestone can add the frontend workflow as a separately identified companion artifact after ComfyUI itself supplies or verifies the conversion.

## Tradeoffs accepted

- We accept API-format JSON without layout in exchange for one exact submitted source of truth and a separately hashed server-accepted graph.
- We accept canonical JSON bytes in exchange for deterministic artifacts and request hashes.
- We accept one existing-input edit in exchange for avoiding a generic JSON patch language.
- We accept mutable run state in application-owned tables in exchange for crash recovery and resumable polling.
- We accept image-only output retention in exchange for a complete, tested output path.
- We accept incomplete environment provenance in exchange for honest claims about what the server run proves.

## Alternatives considered

An offline-only workspace is smaller, but it tests only JSON editing and leaves ComfyUI execution unproven.

An atomic frontend-workflow and API-prompt bundle preserves both documents, but no verified rule proves that the pair represents one editor state. It also makes every API-only edit create stale frontend state.

A generic core run table would reduce duplicate SQL, but XenoDream validation and ComfyUI generation have different states and outputs. Two implementations are not enough evidence for one public run model.

WebSocket completion would report progress, but history polling survives client restarts and needs no added dependency. Progress can be added without changing stored run identity.

## Open questions and risks

- Which custom-node output kinds should M23 retain after image output?
- Should a future local environment snapshot hash model files and custom-node repositories before allowing a reproducibility claim?
- Should frontend workflow JSON become a companion artifact or a separate linked workspace?
- Which server versions after 0.3.45 retain compatible history semantics?

## Verification

Unit tests use a scripted client for workflow acceptance, durable submission, resume without resubmission, and output retention. A live smoke test launches only the installed ComfyUI 0.3.45 process on an unused loopback port with custom nodes disabled and isolated user, output, and temp directories. The workflow uses built-in `EmptyImage -> SaveImage`, so it needs no model. The smoke test proves that the packaged executable revises a workflow, queues the selected revision, retains the PNG, and leaves `HEAD` unchanged.

Official format references:

- [ComfyUI workflow API format](https://github.com/Comfy-Org/docs/blob/main/development/api-development/workflow-api-format.mdx)
- [ComfyUI workflow JSON schema](https://github.com/Comfy-Org/docs/blob/main/specs/workflow_json.mdx)
- [ComfyUI workflow metadata](https://github.com/Comfy-Org/docs/blob/main/development/api-development/workflow-metadata.mdx)

## Result

The packaged live run succeeded against ComfyUI 0.3.45. It executed revision
`55769af7f14f281fdc8dcb4e4b7327bf61c1310a04c2af44b7094e7cf8d3d4b7`
and retained a 441-byte PNG with SHA-256
`597d5bec0035eb1bb05164014ab4ebc55f460b06cc60dcc503a2631d2fd19377`.
