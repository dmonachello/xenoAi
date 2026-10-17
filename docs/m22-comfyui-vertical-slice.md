# ComfyUI API-workflow vertical slice

Date: 2026-10-17

M22 proves that XenoSculpt's revision core can support an application with a
document and runtime model unlike XenoDream. The integration treats ComfyUI
API-format JSON as the native revision artifact. It does not accept or recreate
the frontend workflow format that contains editor layout, groups, and other UI
state.

## Supported workflow

`xenosculpt comfyui init` admits a nonempty graph whose node IDs are decimal
strings. Every node must have a nonempty `class_type` and an `inputs` object.
The parser rejects duplicate keys, byte-order marks, non-finite numbers,
frontend workflow JSON, and links to missing nodes. Tool-authored revisions use
canonical UTF-8 JSON.

`set-input` changes one input that already exists. A literal value uses
`--value-json`. A connection uses `--link-node` and `--link-output`. No-op edits
do not advance `HEAD`. Comparison recursively reports all JSON changes with
JSON Pointer paths.

## Execution model

`run` binds the current revision hash to a caller-generated prompt ID and stores
that request before network I/O. It then checks `/system_stats`, submits through
`POST /prompt`, and polls `/history/{prompt_id}`. The client never retries the
POST because ComfyUI 0.3.45 does not make a same-ID retry idempotent. `resume`
polls the recorded prompt without submitting it again.

Loopback servers are allowed by default. Remote origins require explicit
opt-in. Responses and downloads are bounded, redirects are rejected, and
server filenames never become local paths. Successful PNG, JPEG, and WebP
outputs are stored under `run-artifacts` by content hash.

The run proves that the selected graph was submitted to the recorded ComfyUI
version and that the server's accepted graph produced the retained bytes.
XenoSculpt records separate hashes for the submitted and accepted prompts
because ComfyUI may normalize input values during validation. It does not yet
capture model hashes, input-asset hashes, custom-node commits, or a complete
dependency lock.

Every run also retains and reports the server's `/system_stats` snapshot and
ComfyUI version. Definite prompt-validation errors are terminal rejections;
execution errors retain the server's structured diagnostic messages. Transport
failures after submission remain explicitly ambiguous and are never retried.

## Live verification

The standalone `xenosculpt.exe` was tested against the installed ComfyUI
0.3.45 at commit `9a470e0`. The isolated server used loopback port 8199, disabled
custom nodes, and used separate user, output, and temp directories. The built-in
`EmptyImage -> SaveImage` graph required no model.

The packaged run succeeded for revision
`55769af7f14f281fdc8dcb4e4b7327bf61c1310a04c2af44b7094e7cf8d3d4b7`.
It retained a 441-byte PNG with SHA-256
`597d5bec0035eb1bb05164014ab4ebc55f460b06cc60dcc503a2631d2fd19377`.

The installed ComfyUI directory was not modified. Its existing
`extra_model_paths.yaml` uses a newer list-shaped format that 0.3.45 cannot
parse, so the smoke test used a copied `main.py` entry point outside that
directory to bypass that optional local configuration file.

## Limits

- API-format JSON is an execution artifact, not an editable frontend workflow.
- M22 changes existing inputs; it does not add or remove graph nodes.
- Image outputs are retained. Other output kinds are not yet imported.
- ComfyUI 0.3.45 is the tested target. Other versions require an explicit
  override.
- Run state belongs to the ComfyUI integration. It is not a universal core
  execution schema.

The detailed design is in
[`.architect/m22-comfyui-vertical-slice/design.md`](../.architect/m22-comfyui-vertical-slice/design.md).
