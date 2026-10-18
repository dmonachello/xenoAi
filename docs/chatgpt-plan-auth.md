# ChatGPT-plan authentication

XenoSculpt can use an eligible ChatGPT plan for its natural-language creation
request. This is separate from API-key billing.

## Connect an account

Run:

```powershell
.\dist\xenosculpt.exe auth login
```

XenoSculpt starts a temporary callback listener on `127.0.0.1`, opens the
system browser, and asks you to Continue with ChatGPT. The browser consent must
include permission to use your ChatGPT plan. After authorization, the CLI
prints a redacted local account ID and masked email address.

List the models available to the connected account:

```powershell
.\dist\xenosculpt.exe auth models
```

Use one of those exact IDs with `xenosculpt create`. ChatGPT-plan credentials
are the default for that command. To bill an API project instead, set
`OPENAI_API_KEY` and pass `--auth api-key` explicitly.

## Manage accounts

```powershell
xenosculpt auth status
xenosculpt auth login --new
xenosculpt auth login --account ACCOUNT_ID
xenosculpt auth use ACCOUNT_ID
xenosculpt auth logout --account ACCOUNT_ID
```

`logout` stops local use and attempts to revoke the renewable session. If the
network prevents confirmation, the command reports that remote revocation was
not confirmed. You can also disconnect XenoSculpt in ChatGPT settings.

## Stored data

XenoSculpt stores the following under `%LOCALAPPDATA%\XenoSculpt\auth`:

- a random host identifier;
- the issued OAuth client registration;
- the OpenAI account subject and display label;
- access, refresh, and retained identity tokens;
- granted scopes and expiration times.

Windows DPAPI encrypts the file for the current Windows user. XenoSculpt does
not store credentials in `.xsp` workspaces, XDX files, revision metadata, or
the repository. It does not receive access to ChatGPT conversations.

The program contacts `auth.openai.com` for authorization, token renewal,
identity keys, and revocation. It contacts `api.openai.com/v1` for the model
list and Responses requests. Creation requests use `store: false`.

ChatGPT-plan use depends on OpenAI eligibility, the selected account and
workspace, available models, and usage limits. It is not an unlimited API
allowance. See OpenAI's [Sign in with ChatGPT documentation](https://developers.openai.com/siwc/token-sharing-open-source).
