"""DPAPI-protected, atomically replaced ChatGPT credential storage."""

from __future__ import annotations

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import hmac
import json
import os
from pathlib import Path
import tempfile
from typing import Iterator


class AuthStorageError(RuntimeError):
    pass


class Secret:
    __slots__ = ("__value",)

    def __init__(self, value: str) -> None:
        if not isinstance(value, str) or not value:
            raise ValueError("secret must be non-empty text")
        self.__value = value

    def reveal(self) -> str:
        return self.__value

    def __repr__(self) -> str:
        return "Secret(<redacted>)"

    __str__ = __repr__

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Secret) and hmac.compare_digest(
            self.__value.encode("utf-8"), other.__value.encode("utf-8")
        )


@dataclass(frozen=True, slots=True, repr=False)
class TokenSet:
    access_token: Secret
    refresh_token: Secret
    id_token: Secret
    token_type: str
    expires_at: int
    earliest_refresh_at: int | None
    scopes: tuple[str, ...]


@dataclass(frozen=True, slots=True, repr=False)
class StoredAccount:
    account_id: str
    issuer: str
    subject: str
    email: str | None
    display_name: str | None
    client_id: str
    tokens: TokenSet | None


@dataclass(frozen=True, slots=True, repr=False)
class AuthState:
    version: int
    host_id: str
    active_account_id: str | None
    accounts: tuple[StoredAccount, ...]


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[_DataBlob, object]:
    buffer = ctypes.create_string_buffer(data)
    return (
        _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))),
        buffer,
    )


def _protect(data: bytes) -> bytes:
    if os.name != "nt":
        raise AuthStorageError("ChatGPT credential storage requires Windows")
    source, keepalive = _blob(data)
    output = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    if not crypt32.CryptProtectData(
        ctypes.byref(source),
        "XenoSculpt ChatGPT credentials",
        None,
        None,
        None,
        0x1,
        ctypes.byref(output),
    ):
        raise AuthStorageError("Windows could not protect ChatGPT credentials")
    try:
        result = ctypes.string_at(output.pbData, output.cbData)
        del keepalive
        return result
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def _unprotect(data: bytes) -> bytes:
    if os.name != "nt":
        raise AuthStorageError("ChatGPT credential storage requires Windows")
    source, keepalive = _blob(data)
    output = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    if not crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0x1, ctypes.byref(output)
    ):
        raise AuthStorageError("ChatGPT credential storage is unreadable")
    try:
        result = ctypes.string_at(output.pbData, output.cbData)
        del keepalive
        return result
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def _encode(state: AuthState) -> bytes:
    value = {
        "version": state.version,
        "host_id": state.host_id,
        "active_account_id": state.active_account_id,
        "accounts": [
            {
                "account_id": item.account_id,
                "issuer": item.issuer,
                "subject": item.subject,
                "email": item.email,
                "display_name": item.display_name,
                "client_id": item.client_id,
                "tokens": None
                if item.tokens is None
                else {
                    "access_token": item.tokens.access_token.reveal(),
                    "refresh_token": item.tokens.refresh_token.reveal(),
                    "id_token": item.tokens.id_token.reveal(),
                    "token_type": item.tokens.token_type,
                    "expires_at": item.tokens.expires_at,
                    "earliest_refresh_at": item.tokens.earliest_refresh_at,
                    "scopes": list(item.tokens.scopes),
                },
            }
            for item in state.accounts
        ],
    }
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _decode(data: bytes) -> AuthState:
    try:
        value = json.loads(data)
        if not isinstance(value, dict) or set(value) != {
            "version", "host_id", "active_account_id", "accounts"
        }:
            raise ValueError("unexpected fields")
        if value["version"] != 1 or not isinstance(value["host_id"], str):
            raise ValueError("unsupported state")
        active = value["active_account_id"]
        if active is not None and not isinstance(active, str):
            raise ValueError("invalid active account")
        raw_accounts = value["accounts"]
        if not isinstance(raw_accounts, list):
            raise ValueError("accounts must be an array")
        accounts: list[StoredAccount] = []
        for raw in raw_accounts:
            if not isinstance(raw, dict) or set(raw) != {
                "account_id", "issuer", "subject", "email", "display_name", "client_id", "tokens"
            }:
                raise ValueError("invalid account record")
            token_value = raw["tokens"]
            tokens = None
            if token_value is not None:
                if not isinstance(token_value, dict) or set(token_value) != {
                    "access_token", "refresh_token", "id_token", "token_type",
                    "expires_at", "earliest_refresh_at", "scopes"
                }:
                    raise ValueError("invalid token record")
                scopes = token_value["scopes"]
                if not isinstance(scopes, list) or not all(isinstance(x, str) for x in scopes):
                    raise ValueError("invalid token scopes")
                tokens = TokenSet(
                    Secret(token_value["access_token"]),
                    Secret(token_value["refresh_token"]),
                    Secret(token_value["id_token"]),
                    token_value["token_type"],
                    token_value["expires_at"],
                    token_value["earliest_refresh_at"],
                    tuple(scopes),
                )
            accounts.append(
                StoredAccount(
                    raw["account_id"], raw["issuer"], raw["subject"], raw["email"],
                    raw["display_name"], raw["client_id"], tokens
                )
            )
        ids = {item.account_id for item in accounts}
        if len(ids) != len(accounts) or (active is not None and active not in ids):
            raise ValueError("invalid account selection")
        return AuthState(1, value["host_id"], active, tuple(accounts))
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuthStorageError(f"ChatGPT credential state is invalid: {error}") from error


def default_auth_path() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        raise AuthStorageError("LOCALAPPDATA is unavailable")
    return Path(root) / "XenoSculpt" / "auth" / "v1" / "credentials.bin"


class FileAuthStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = default_auth_path() if path is None else Path(path)

    def load(self) -> AuthState | None:
        if not self.path.exists():
            return None
        try:
            encrypted = self.path.read_bytes()
        except OSError as error:
            raise AuthStorageError(f"cannot read ChatGPT credential state: {error}") from error
        if not encrypted:
            raise AuthStorageError("ChatGPT credential state is empty")
        return _decode(_unprotect(encrypted))

    def save(self, state: AuthState) -> None:
        encrypted = _protect(_encode(state))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd, raw_path = tempfile.mkstemp(prefix="credentials-", suffix=".tmp", dir=self.path.parent)
            temp = Path(raw_path)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(encrypted)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp, self.path)
            finally:
                if temp.exists():
                    temp.unlink()
        except OSError as error:
            raise AuthStorageError(f"cannot save ChatGPT credential state: {error}") from error


def _current_user_sid() -> str:
    if os.name != "nt":
        raise AuthStorageError("ChatGPT credential locking requires Windows")
    kernel32 = ctypes.windll.kernel32
    advapi32 = ctypes.windll.advapi32
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    advapi32.OpenProcessToken.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    )
    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.GetTokenInformation.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    advapi32.GetTokenInformation.restype = wintypes.BOOL
    advapi32.ConvertSidToStringSidW.argtypes = (
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.LPWSTR),
    )
    advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(
        kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)
    ):
        raise AuthStorageError("cannot inspect Windows user identity")
    try:
        needed = wintypes.DWORD()
        advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(needed))
        buffer = ctypes.create_string_buffer(needed.value)
        if not advapi32.GetTokenInformation(token, 1, buffer, needed, ctypes.byref(needed)):
            raise AuthStorageError("cannot inspect Windows user identity")
        sid_pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        text = wintypes.LPWSTR()
        if not advapi32.ConvertSidToStringSidW(sid_pointer, ctypes.byref(text)):
            raise AuthStorageError("cannot inspect Windows user identity")
        try:
            return text.value
        finally:
            kernel32.LocalFree(text)
    finally:
        kernel32.CloseHandle(token)


@contextmanager
def auth_lock(*, timeout_ms: int = 30_000) -> Iterator[None]:
    if os.name != "nt":
        raise AuthStorageError("ChatGPT credential locking requires Windows")
    import hashlib

    suffix = hashlib.sha256(_current_user_sid().encode("ascii")).hexdigest()[:20]
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    handle = kernel32.CreateMutexW(None, False, f"Global\\XenoSculpt.ChatGPT.Auth.{suffix}")
    if not handle:
        raise AuthStorageError("cannot create ChatGPT credential mutex")
    acquired = False
    try:
        wait = kernel32.WaitForSingleObject(handle, timeout_ms)
        if wait not in (0x00000000, 0x00000080):
            if wait == 0x00000102:
                raise AuthStorageError("another XenoSculpt authentication update is running")
            raise AuthStorageError("cannot acquire ChatGPT credential mutex")
        acquired = True
        yield
    finally:
        if acquired:
            kernel32.ReleaseMutex(handle)
        kernel32.CloseHandle(handle)
