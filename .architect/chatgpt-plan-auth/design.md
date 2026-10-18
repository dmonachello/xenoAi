# ChatGPT-plan authentication

## Problem

XenoSculpt currently sends natural-language creation requests with
`OPENAI_API_KEY`, so OpenAI bills the API organization rather than the user's
ChatGPT plan. Sign in with ChatGPT is a different protocol, not a bearer-token
substitution. It requires browser OAuth with PKCE, validated OIDC identity,
protected rotating credentials, serialized refresh, and a restricted streaming
Responses request. These concerns must stay outside XDX mutation and the shared
revision core.

This milestone also makes the repository open source under MIT. The public
license and package metadata must exist before documentation describes the app
as an open-source client.

## Usage

The normal personal workflow is:

```powershell
.\dist\xenosculpt.exe auth login

.\dist\xenosculpt.exe create .\output\sculpture.xsp `
  --prompt "Make a broad cube with a cushioned sphere 55 units to its right" `
  --model MODEL_FROM_AUTH_MODELS `
  --export .\output\sculpture.xxp
```

`auth login` starts a listener on `127.0.0.1`, opens the system browser, and
prints only redacted account state. It never prints an authorization URL or
token. `create` uses the active ChatGPT registration by default. It fails with
an instruction to run `auth login` when no usable registration exists.

API-key billing remains an explicit fallback:

```powershell
$env:OPENAI_API_KEY = "..."
.\dist\xenosculpt.exe create .\output\sculpture.xsp `
  --prompt "Make a broad cube" --model gpt-4o-mini --auth api-key
```

There is no automatic fallback between billing sources. Other auth commands
are deliberately small:

```powershell
xenosculpt auth status
xenosculpt auth models
xenosculpt auth login --new
xenosculpt auth login --account ACCOUNT_ID
xenosculpt auth use ACCOUNT_ID
xenosculpt auth logout [--account ACCOUNT_ID]
```

## Shape

### Domain types

```python
class AuthorizationKind(StrEnum):
    CHATGPT_PLAN = "chatgpt-plan"
    API_KEY = "api-key"

@dataclass(frozen=True, slots=True, repr=False)
class Secret:
    value: str

@dataclass(frozen=True, slots=True)
class AccountSummary:
    account_id: str
    masked_email: str | None
    connected: bool
    plan_usage_enabled: bool
    active: bool

@dataclass(frozen=True, slots=True, repr=False)
class AccessLease:
    authorization: Secret
    account_id: str
    expires_at: datetime

@dataclass(frozen=True, slots=True)
class CompletedTextResponse:
    response_id: str
    model: str
    text: str
```

Secret-bearing types have redacted `repr` and no public JSON serializer.
Account identities are keyed by validated issuer, issued client ID, and subject.
Email is display data only.

### Interfaces

```python
class ChatGPTPlanAuth:
    def login(self, account_id: str | None = None, *, new: bool = False) -> AccountSummary: ...
    def accounts(self) -> tuple[AccountSummary, ...]: ...
    def select(self, account_id: str) -> AccountSummary: ...
    def acquire(self, account_id: str | None = None) -> AccessLease: ...
    def models(self, account_id: str | None = None) -> tuple[str, ...]: ...
    def logout(self, account_id: str | None = None) -> LogoutResult: ...

class ResponsesClient:
    def complete_structured(
        self,
        request: StructuredTextRequest,
        *,
        authorization: ResponsesAuthorization,
        timeout_seconds: float,
    ) -> CompletedTextResponse: ...
```

`request_creation()` remains the API-key compatibility seam for Python callers.
The CLI resolves `--auth` and calls a new authorized planner entry point. The
planner still owns only XenoDream instructions, schema, and recipe decoding.

### Module map

```text
src/xenosculpt_openai/
  auth.py       lifecycle and account selection
  oidc.py       discovery, PKCE, callback, token exchange, JWT verification
  storage.py    DPAPI records, atomic replacement, Windows mutex
  responses.py  API-key JSON and ChatGPT-plan SSE request policies
  cli.py        redacted auth commands

src/xenodream_xxp/openai_planner.py
  XenoDream instructions/schema and ModelCreation conversion

src/xenosculpt/cli.py
  routes the top-level auth command
```

The sibling package avoids cycles and keeps OAuth out of `xenosculpt.core`,
ComfyUI, MoI, and XDX semantics.

### Security and protocol invariants

- Bind the callback only to literal `127.0.0.1` and exact `/auth/callback`.
- Start the listener before opening the system browser.
- Generate fresh state, nonce, and PKCE S256 values for every attempt.
- Use `dynamic_agent_client` only for registration. Exchange with and persist
  the issued client ID.
- Verify the ID-token signature with a maintained JWT/JWK library. Require the
  exact issuer, client-ID audience, expiry, nonce, and nonempty subject.
- Require `chatgpt.tokens.use.direct` before inference.
- Store credentials under `%LOCALAPPDATA%\XenoSculpt\auth`, encrypted with
  current-user DPAPI. Never store them in a workspace or beside the executable.
- Serialize each account's load, refresh, and atomic replacement with a
  cross-process Windows mutex. Reload after acquiring the mutex.
- Never print or log tokens, callback queries, authorization URLs, subjects,
  client IDs, host IDs, nonce, state, or PKCE material.
- Never fall back to another billing source after an auth or inference failure.
- Revoke on logout when possible, always stop local use, and report honestly
  when remote revocation is unconfirmed.

ChatGPT-plan inference sends `store:false`, `stream:true`, array-form input, and
omits `max_output_tokens` and every currently unsupported field. A bounded SSE
decoder accepts exactly one terminal `response.completed`. Failed, incomplete,
refused, malformed, oversized, duplicated-terminal, or prematurely closed
streams produce no `ModelCreation` and no workspace writes.

API-key inference retains the existing non-streaming request for compatibility.
Both modes return the same completed domain response to the XenoDream planner.

## Synthesis decision

The secure candidate is the base because billing-source clarity and credential
integrity matter more than the smallest implementation. The runtime candidate
contributes the sibling `xenosculpt_openai` package and the strict terminal SSE
decoder. The simple candidate contributes the compact top-level auth commands.

The secure candidate required a credential flag on every creation. That was
rejected as needless friction for this personal application. A successful
ChatGPT login makes ChatGPT-plan usage the CLI default. API-key billing requires
`--auth api-key`, so failure never causes a silent charge. The simple
candidate's `auto` fallback was rejected for that reason.

## Tradeoffs accepted

- Windows-only persistent ChatGPT credentials are accepted because the shipped
  XenoDream tool is Windows-only. API-key use remains portable.
- A JWT/cryptography dependency is accepted instead of handwritten signature
  verification.
- Reauthorization may be required if the process crashes after server-side
  refresh rotation but before atomic local replacement.
- Multiple account records are supported because an issued client ID is bound
  to a specific account and workspace.
- OpenAI's plan-sharing contract is a preview and may require maintenance.

## Alternatives considered

- Treating the OAuth token as an API key was rejected because it produces an
  invalid SIWC request and has no refresh or identity safety.
- Running Codex app-server was rejected because this app needs one bounded
  structured translation, not an agent subprocess and RPC lifecycle.
- Storing tokens as plaintext JSON was rejected. Tokens are current-user DPAPI
  ciphertext plus user-scoped filesystem permissions.
- Putting auth in `xenodream_xxp` or `xenosculpt.core` was rejected because
  account lifecycle is provider infrastructure, not document or revision logic.

## Verification sequence

1. Add MIT license and package metadata.
2. Add failing protocol tests for PKCE/callback/OIDC and SSE completion.
3. Implement protected storage and cross-process refresh tests.
4. Add auth CLI and create-source selection tests, including no-write failures.
5. Run the full suite and reference verifier.
6. Build the one-file executable and test auth help/status from a clean folder.
7. Run one real browser login and streamed dry-run with the user's eligible
   account. Retain only redacted evidence.

Stop on any credential leak, invalid identity acceptance, refresh race, silent
billing fallback, partial-stream acceptance, workspace write after auth failure,
or cross-application regression.
