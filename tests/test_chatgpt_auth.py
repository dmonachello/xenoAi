from __future__ import annotations

from datetime import UTC, datetime
import base64
import json
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from xenosculpt_openai.auth import (
    AccessLease,
    AccountSummary,
    AuthError,
    AuthorizationKind,
    ChatGPTPlanAuth,
)
from xenosculpt_openai.oidc import (
    OidcError,
    build_authorization_url,
    make_pkce,
    parse_callback,
    verify_id_token,
)
from xenosculpt_openai.storage import (
    AuthState,
    FileAuthStore,
    Secret,
    StoredAccount,
    TokenSet,
)


def test_secret_never_reveals_value_in_text_or_repr() -> None:
    secret = Secret("sensitive-token")
    assert "sensitive-token" not in str(secret)
    assert "sensitive-token" not in repr(secret)
    assert secret.reveal() == "sensitive-token"


def test_public_auth_records_do_not_contain_tokens() -> None:
    summary = AccountSummary(
        account_id="acct_test",
        masked_email="u***@example.com",
        connected=True,
        plan_usage_enabled=True,
        active=True,
    )
    lease = AccessLease(
        authorization=Secret("access-token"),
        account_id="acct_test",
        expires_at=datetime(2026, 10, 18, tzinfo=UTC),
    )

    assert "token" not in repr(summary).lower()
    assert "access-token" not in repr(lease)
    assert AuthorizationKind.CHATGPT_PLAN.value == "chatgpt-plan"


def test_pkce_and_authorization_url_use_required_plan_scopes() -> None:
    verifier, challenge = make_pkce(random_bytes=b"a" * 48)
    assert "=" not in verifier
    assert "=" not in challenge
    url = build_authorization_url(
        client_id="dynamic_agent_client",
        redirect_uri="http://127.0.0.1:43123/auth/callback",
        state="state-value",
        nonce="nonce-value",
        code_challenge=challenge,
        host_id="urn:uuid:11111111-1111-4111-8111-111111111111",
        new_registration=True,
    )
    assert "localhost" not in url
    assert "chatgpt.tokens.use.direct" in url
    assert "agent_name_hint=XenoSculpt" in url


def test_callback_requires_state_and_issued_client_for_registration() -> None:
    with pytest.raises(OidcError, match="state"):
        parse_callback("code=a&state=wrong", expected_state="right", returning_client_id=None)
    with pytest.raises(OidcError, match="issued client"):
        parse_callback("code=a&state=right", expected_state="right", returning_client_id=None)
    result = parse_callback(
        "code=a&state=right&client_id=oaiapp_test",
        expected_state="right",
        returning_client_id=None,
    )
    assert result.client_id == "oaiapp_test"


def test_id_token_verification_checks_signature_audience_and_nonce() -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_numbers()

    def encoded(value: int) -> str:
        raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key",
                "use": "sig",
                "alg": "RS256",
                "n": encoded(public.n),
                "e": encoded(public.e),
            }
        ]
    }
    claims = {
        "iss": "https://auth.openai.com",
        "aud": "oaiapp_test",
        "sub": "subject",
        "email": "user@example.com",
        "nonce": "nonce",
        "iat": 1792340000,
        "exp": 1792343600,
    }
    token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test-key"})
    identity = verify_id_token(
        token,
        client_id="oaiapp_test",
        nonce="nonce",
        jwks=jwks,
        now=datetime.fromtimestamp(1792340100, UTC),
    )
    assert identity.subject == "subject"
    with pytest.raises(OidcError):
        verify_id_token(
            token,
            client_id="wrong-client",
            nonce="nonce",
            jwks=jwks,
            now=datetime.fromtimestamp(1792340100, UTC),
        )


def test_dpapi_store_roundtrips_without_plaintext_tokens(tmp_path: Path) -> None:
    tokens = TokenSet(
        access_token=Secret("access-secret"),
        refresh_token=Secret("refresh-secret"),
        id_token=Secret("id-secret"),
        token_type="Bearer",
        expires_at=1792343600,
        earliest_refresh_at=None,
        scopes=("chatgpt.tokens.use.direct", "offline_access"),
    )
    state = AuthState(
        version=1,
        host_id="urn:uuid:11111111-1111-4111-8111-111111111111",
        active_account_id="acct_test",
        accounts=(
            StoredAccount(
                account_id="acct_test",
                issuer="https://auth.openai.com",
                subject="subject",
                email="user@example.com",
                display_name="User",
                client_id="oaiapp_test",
                tokens=tokens,
            ),
        ),
    )
    store = FileAuthStore(tmp_path / "auth.bin")
    store.save(state)
    raw = (tmp_path / "auth.bin").read_bytes()
    assert b"access-secret" not in raw
    assert b"refresh-secret" not in raw
    loaded = store.load()
    assert loaded == state


def test_first_login_persists_host_identity_before_opening_browser(tmp_path: Path) -> None:
    store = FileAuthStore(tmp_path / "auth.bin")
    observed: list[AuthState | None] = []

    def inspect_then_refuse(_url: str) -> bool:
        observed.append(store.load())
        return False

    auth = ChatGPTPlanAuth(store, browser_open=inspect_then_refuse)
    with pytest.raises(AuthError, match="could not open"):
        auth.login(timeout_seconds=1)

    assert observed[0] is not None
    assert store.load() == observed[0]
