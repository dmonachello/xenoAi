"""Public, non-secret authentication values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import secrets
import time
from typing import Callable
from uuid import uuid4
import webbrowser

from .oidc import (
    ISSUER,
    SCOPES,
    LoopbackCallback,
    OidcError,
    build_authorization_url,
    exchange_code,
    fetch_jwks,
    make_pkce,
    parse_callback,
    refresh_tokens,
    revoke_token,
    verify_id_token,
)
from .responses import list_chatgpt_models
from .storage import (
    AuthState,
    AuthStorageError,
    FileAuthStore,
    Secret,
    StoredAccount,
    TokenSet,
    auth_lock,
)


class AuthorizationKind(StrEnum):
    CHATGPT_PLAN = "chatgpt-plan"
    API_KEY = "api-key"


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

    def __repr__(self) -> str:
        return (
            f"AccessLease(account_id={self.account_id!r}, "
            f"expires_at={self.expires_at!r}, authorization=<redacted>)"
        )


class AuthError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LogoutResult:
    account_id: str
    local_credentials_cleared: bool
    remote_revocation_confirmed: bool


def _mask_email(value: str | None) -> str | None:
    if value is None or "@" not in value:
        return None
    local, domain = value.split("@", 1)
    return f"{local[:1]}***@{domain}"


def _summary(account: StoredAccount, *, active: bool) -> AccountSummary:
    scopes = () if account.tokens is None else account.tokens.scopes
    return AccountSummary(
        account.account_id,
        _mask_email(account.email),
        account.tokens is not None,
        "chatgpt.tokens.use.direct" in scopes,
        active,
    )


def _new_state() -> AuthState:
    return AuthState(1, f"urn:uuid:{uuid4()}", None, ())


def _replace_account(state: AuthState, account: StoredAccount, *, active: bool) -> AuthState:
    accounts = tuple(item for item in state.accounts if item.account_id != account.account_id) + (account,)
    return AuthState(
        1,
        state.host_id,
        account.account_id if active else state.active_account_id,
        accounts,
    )


class ChatGPTPlanAuth:
    def __init__(
        self,
        store: FileAuthStore | None = None,
        *,
        browser_open: Callable[[str], bool] = webbrowser.open,
    ) -> None:
        self.store = FileAuthStore() if store is None else store
        self.browser_open = browser_open

    def _load(self) -> AuthState:
        return self.store.load() or _new_state()

    def accounts(self) -> tuple[AccountSummary, ...]:
        state = self._load()
        return tuple(
            _summary(item, active=item.account_id == state.active_account_id)
            for item in state.accounts
        )

    def select(self, account_id: str) -> AccountSummary:
        with auth_lock():
            state = self._load()
            matches = [item for item in state.accounts if item.account_id == account_id]
            if len(matches) != 1:
                raise AuthError("unknown ChatGPT account")
            selected = matches[0]
            state = AuthState(1, state.host_id, account_id, state.accounts)
            self.store.save(state)
            return _summary(selected, active=True)

    def login(
        self,
        account_id: str | None = None,
        *,
        new: bool = False,
        timeout_seconds: float = 180,
    ) -> AccountSummary:
        state = self._load()
        existing: StoredAccount | None = None
        if new and account_id is not None:
            raise AuthError("--new and --account cannot be combined")
        if not new:
            selected_id = account_id or state.active_account_id
            if selected_id is not None:
                existing = next(
                    (item for item in state.accounts if item.account_id == selected_id), None
                )
                if existing is None:
                    raise AuthError("unknown ChatGPT account")
            elif state.accounts:
                if len(state.accounts) != 1:
                    raise AuthError("select an account or use --new")
                existing = state.accounts[0]
        registration_client = "dynamic_agent_client" if existing is None else existing.client_id
        verifier, challenge = make_pkce()
        oauth_state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        with LoopbackCallback() as callback:
            url = build_authorization_url(
                client_id=registration_client,
                redirect_uri=callback.redirect_uri,
                state=oauth_state,
                nonce=nonce,
                code_challenge=challenge,
                host_id=state.host_id,
                new_registration=existing is None,
                id_token_hint=None
                if existing is None or existing.tokens is None
                else existing.tokens.id_token.reveal(),
                login_hint=None if existing is None else existing.email,
            )
            if not self.browser_open(url):
                raise AuthError("could not open the system browser for ChatGPT sign-in")
            query = callback.wait(timeout_seconds=timeout_seconds)
            result = parse_callback(
                query,
                expected_state=oauth_state,
                returning_client_id=None if existing is None else existing.client_id,
            )
            token_result = exchange_code(
                client_id=result.client_id,
                code=result.code,
                code_verifier=verifier,
                redirect_uri=callback.redirect_uri,
            )
        if "chatgpt.tokens.use.direct" not in token_result.scopes:
            raise AuthError("ChatGPT plan permission was not granted")
        if token_result.id_token is None:
            raise AuthError("OpenAI did not return an identity token")
        identity = verify_id_token(
            token_result.id_token,
            client_id=result.client_id,
            nonce=nonce,
            jwks=fetch_jwks(),
        )
        if existing is not None and identity.subject != existing.subject:
            raise AuthError("ChatGPT returned a different account during reauthentication")
        now = int(time.time())
        account = StoredAccount(
            existing.account_id if existing is not None else f"acct_{uuid4().hex[:16]}",
            ISSUER,
            identity.subject,
            identity.email,
            identity.display_name,
            result.client_id,
            TokenSet(
                Secret(token_result.access_token),
                Secret(token_result.refresh_token),
                Secret(token_result.id_token),
                token_result.token_type,
                now + token_result.expires_in,
                token_result.earliest_refresh_at,
                token_result.scopes,
            ),
        )
        with auth_lock():
            latest = self._load()
            if latest.host_id != state.host_id:
                raise AuthError("ChatGPT host identity changed during sign-in")
            self.store.save(_replace_account(latest, account, active=True))
        return _summary(account, active=True)

    def acquire(self, account_id: str | None = None) -> AccessLease:
        with auth_lock():
            state = self._load()
            selected_id = account_id or state.active_account_id
            if selected_id is None:
                raise AuthError("no active ChatGPT account; run 'xenosculpt auth login'")
            account = next(
                (item for item in state.accounts if item.account_id == selected_id), None
            )
            if account is None or account.tokens is None:
                raise AuthError("ChatGPT account requires sign-in")
            tokens = account.tokens
            if "chatgpt.tokens.use.direct" not in tokens.scopes:
                raise AuthError("ChatGPT plan permission is not enabled")
            now = int(time.time())
            if tokens.expires_at <= now + 300:
                if tokens.earliest_refresh_at is not None and now < tokens.earliest_refresh_at:
                    raise AuthError("ChatGPT access expires before refresh is allowed")
                refreshed = refresh_tokens(
                    client_id=account.client_id,
                    refresh_token=tokens.refresh_token.reveal(),
                )
                scopes = refreshed.scopes
                if "chatgpt.tokens.use.direct" not in scopes:
                    raise AuthError("refreshed ChatGPT session lacks plan permission")
                id_token = tokens.id_token if refreshed.id_token is None else Secret(refreshed.id_token)
                tokens = TokenSet(
                    Secret(refreshed.access_token),
                    Secret(refreshed.refresh_token),
                    id_token,
                    refreshed.token_type,
                    now + refreshed.expires_in,
                    refreshed.earliest_refresh_at,
                    scopes,
                )
                account = StoredAccount(
                    account.account_id, account.issuer, account.subject, account.email,
                    account.display_name, account.client_id, tokens
                )
                self.store.save(_replace_account(state, account, active=False))
            return AccessLease(
                tokens.access_token,
                account.account_id,
                datetime.fromtimestamp(tokens.expires_at, UTC),
            )

    def models(self, account_id: str | None = None) -> tuple[str, ...]:
        return list_chatgpt_models(self.acquire(account_id).authorization)

    def logout(self, account_id: str | None = None) -> LogoutResult:
        with auth_lock():
            state = self._load()
            selected_id = account_id or state.active_account_id
            if selected_id is None:
                raise AuthError("no ChatGPT account is selected")
            account = next(
                (item for item in state.accounts if item.account_id == selected_id), None
            )
            if account is None:
                raise AuthError("unknown ChatGPT account")
            confirmed = True
            if account.tokens is not None:
                confirmed = revoke_token(
                    client_id=account.client_id,
                    refresh_token=account.tokens.refresh_token.reveal(),
                )
            cleared = StoredAccount(
                account.account_id, account.issuer, account.subject, account.email,
                account.display_name, account.client_id, None
            )
            updated = _replace_account(state, cleared, active=False)
            if updated.active_account_id == selected_id:
                updated = AuthState(1, updated.host_id, None, updated.accounts)
            self.store.save(updated)
            return LogoutResult(selected_id, True, confirmed)
