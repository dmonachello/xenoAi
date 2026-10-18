"""Sign in with ChatGPT OIDC and PKCE protocol helpers."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import secrets
import threading
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

import jwt


ISSUER = "https://auth.openai.com"
AUTHORIZE_URL = f"{ISSUER}/api/accounts/authorize"
TOKEN_URL = f"{ISSUER}/api/accounts/oauth/token"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"
RESOURCE = "https://api.openai.com/v1"
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"


class OidcError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CallbackResult:
    code: str
    client_id: str


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    subject: str
    email: str | None
    display_name: str | None


@dataclass(frozen=True, slots=True, repr=False)
class TokenEndpointResult:
    access_token: str
    refresh_token: str
    id_token: str | None
    token_type: str
    expires_in: int
    earliest_refresh_at: int | None
    scopes: tuple[str, ...]


def _read_json(response: object, *, limit: int = 1_000_000) -> dict[str, object]:
    data = response.read(limit + 1)  # type: ignore[attr-defined]
    if len(data) > limit:
        raise OidcError("OpenAI authentication response exceeded its size limit")
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OidcError(f"OpenAI authentication returned invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise OidcError("OpenAI authentication response must be an object")
    return value


def _post_form(url: str, values: dict[str, str], *, timeout_seconds: float) -> dict[str, object]:
    request = Request(
        url,
        data=urlencode(values).encode("ascii"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "xenosculpt-chatgpt-auth/1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return _read_json(response)
    except HTTPError as error:
        detail = error.read(4096).decode("utf-8", errors="replace")
        raise OidcError(f"OpenAI authentication returned HTTP {error.code}: {detail}") from error
    except (URLError, TimeoutError, OSError) as error:
        raise OidcError(f"OpenAI authentication request failed: {error}") from error


def _parse_token_result(value: dict[str, object], *, require_id_token: bool) -> TokenEndpointResult:
    access = value.get("access_token")
    refresh = value.get("refresh_token")
    identity = value.get("id_token")
    token_type = value.get("token_type")
    expires = value.get("expires_in")
    scope = value.get("scope")
    if not isinstance(access, str) or not access:
        raise OidcError("OpenAI token response has no access token")
    if not isinstance(refresh, str) or not refresh:
        raise OidcError("OpenAI token response has no refresh token")
    if require_id_token and (not isinstance(identity, str) or not identity):
        raise OidcError("OpenAI token response has no identity token")
    if identity is not None and not isinstance(identity, str):
        raise OidcError("OpenAI identity token is invalid")
    if token_type != "Bearer":
        raise OidcError("OpenAI token response uses an unsupported token type")
    if isinstance(expires, bool) or not isinstance(expires, int) or expires <= 0:
        raise OidcError("OpenAI token response has an invalid expiration")
    if not isinstance(scope, str):
        raise OidcError("OpenAI token response has no scopes")
    scopes = tuple(sorted(set(scope.split())))
    earliest = value.get("earliest_refresh_at")
    earliest_value: int | None = None
    if earliest is not None:
        if isinstance(earliest, int) and not isinstance(earliest, bool):
            earliest_value = earliest
        elif isinstance(earliest, str):
            try:
                earliest_value = int(
                    datetime.fromisoformat(earliest.replace("Z", "+00:00")).timestamp()
                )
            except ValueError as error:
                raise OidcError("OpenAI token response has an invalid refresh time") from error
        else:
            raise OidcError("OpenAI token response has an invalid refresh time")
    return TokenEndpointResult(
        access, refresh, identity, token_type, expires, earliest_value, scopes
    )


def exchange_code(
    *, client_id: str, code: str, code_verifier: str, redirect_uri: str,
    timeout_seconds: float = 30,
) -> TokenEndpointResult:
    value = _post_form(
        TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "resource": RESOURCE,
        },
        timeout_seconds=timeout_seconds,
    )
    return _parse_token_result(value, require_id_token=True)


def refresh_tokens(
    *, client_id: str, refresh_token: str, timeout_seconds: float = 30
) -> TokenEndpointResult:
    value = _post_form(
        TOKEN_URL,
        {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_token,
            "resource": RESOURCE,
        },
        timeout_seconds=timeout_seconds,
    )
    return _parse_token_result(value, require_id_token=False)


def fetch_jwks(*, timeout_seconds: float = 30) -> dict[str, object]:
    request = Request(JWKS_URL, headers={"User-Agent": "xenosculpt-chatgpt-auth/1"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            value = _read_json(response)
    except HTTPError as error:
        raise OidcError(f"OpenAI identity keys returned HTTP {error.code}") from error
    except (URLError, TimeoutError, OSError) as error:
        raise OidcError(f"OpenAI identity key request failed: {error}") from error
    if not isinstance(value.get("keys"), list):
        raise OidcError("OpenAI identity key set is invalid")
    return value


def revoke_token(
    *, client_id: str, refresh_token: str, timeout_seconds: float = 30
) -> bool:
    request = Request(
        f"{ISSUER}/api/accounts/oauth/revoke",
        data=urlencode(
            {
                "token": refresh_token,
                "token_type_hint": "refresh_token",
                "client_id": client_id,
            }
        ).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.status == 200
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


class LoopbackCallback:
    """One-use loopback listener. It never records or logs the callback URL."""

    def __init__(self) -> None:
        self._query: str | None = None
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urlsplit(self.path)
                if parsed.path != "/auth/callback" or outer._query is not None:
                    self.send_error(404)
                    return
                outer._query = parsed.query
                body = b"XenoSculpt sign-in received. You can close this window."
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                return

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._server.timeout = 0.25
        self._closed = False

    @property
    def redirect_uri(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}/auth/callback"

    def wait(self, *, timeout_seconds: float) -> str:
        deadline = datetime.now(UTC).timestamp() + timeout_seconds
        while self._query is None and datetime.now(UTC).timestamp() < deadline:
            self._server.handle_request()
        if self._query is None:
            raise OidcError("ChatGPT sign-in timed out")
        return self._query

    def close(self) -> None:
        if not self._closed:
            self._server.server_close()
            self._closed = True

    def __enter__(self) -> "LoopbackCallback":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_pkce(*, random_bytes: bytes | None = None) -> tuple[str, str]:
    raw = secrets.token_bytes(48) if random_bytes is None else random_bytes
    if len(raw) < 32:
        raise ValueError("PKCE randomness must contain at least 32 bytes")
    verifier = _b64url(raw)
    return verifier, _b64url(sha256(verifier.encode("ascii")).digest())


def build_authorization_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    nonce: str,
    code_challenge: str,
    host_id: str,
    new_registration: bool,
    id_token_hint: str | None = None,
    login_hint: str | None = None,
) -> str:
    if not redirect_uri.startswith("http://127.0.0.1:") or not redirect_uri.endswith("/auth/callback"):
        raise OidcError("redirect URI must use 127.0.0.1 and /auth/callback")
    values = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "resource": RESOURCE,
        "state": state,
        "nonce": nonce,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
        "ext_agent_host_id": host_id,
    }
    if new_registration:
        values["agent_name_hint"] = "XenoSculpt"
    else:
        if id_token_hint:
            values["id_token_hint"] = id_token_hint
        if login_hint:
            values["login_hint"] = login_hint
    return f"{AUTHORIZE_URL}?{urlencode(values)}"


def parse_callback(
    query: str, *, expected_state: str, returning_client_id: str | None
) -> CallbackResult:
    values = parse_qs(query, keep_blank_values=True, strict_parsing=False)
    if any(len(items) != 1 for items in values.values()):
        raise OidcError("authorization callback contains duplicate parameters")
    if values.get("state") != [expected_state]:
        raise OidcError("authorization callback state did not match")
    if "error" in values:
        raise OidcError("ChatGPT authorization was denied or cancelled")
    code = values.get("code", [None])[0]
    if not isinstance(code, str) or not code:
        raise OidcError("authorization callback did not contain a code")
    returned_client = values.get("client_id", [None])[0]
    if returning_client_id is None:
        if not isinstance(returned_client, str) or not returned_client.startswith("oaiapp_"):
            raise OidcError("authorization callback did not contain an issued client ID")
        client_id = returned_client
    else:
        if returned_client is not None and returned_client != returning_client_id:
            raise OidcError("authorization callback changed the registered client ID")
        client_id = returning_client_id
    return CallbackResult(code, client_id)


def verify_id_token(
    token: str,
    *,
    client_id: str,
    nonce: str,
    jwks: dict[str, object],
    now: datetime | None = None,
) -> VerifiedIdentity:
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        keys = jwks.get("keys")
        if not isinstance(kid, str) or not isinstance(keys, list):
            raise OidcError("OpenAI identity key set is invalid")
        matches = [item for item in keys if isinstance(item, dict) and item.get("kid") == kid]
        if len(matches) != 1:
            raise OidcError("OpenAI identity signing key was not found")
        key = jwt.PyJWK.from_dict(matches[0], algorithm="RS256").key
        options: dict[str, object] = {"require": ["exp", "iat", "iss", "aud", "sub"]}
        if now is not None:
            options["verify_exp"] = False
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=ISSUER,
            options=options,
            leeway=5,
        )
        if now is not None:
            timestamp = int(now.timestamp())
            if not isinstance(claims.get("exp"), int) or claims["exp"] < timestamp - 5:
                raise OidcError("OpenAI identity token expired")
            if isinstance(claims.get("nbf"), int) and claims["nbf"] > timestamp + 5:
                raise OidcError("OpenAI identity token is not valid yet")
        if claims.get("nonce") != nonce:
            raise OidcError("OpenAI identity nonce did not match")
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise OidcError("OpenAI identity token has no subject")
        email = claims.get("email") if isinstance(claims.get("email"), str) else None
        name = claims.get("name") if isinstance(claims.get("name"), str) else None
        return VerifiedIdentity(subject, email, name)
    except OidcError:
        raise
    except jwt.PyJWTError as error:
        raise OidcError(f"OpenAI identity token was rejected: {error}") from error
