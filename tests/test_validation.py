from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from xenodream_xxp.native_export import MeshExportSettings
from xenodream_xxp.validation import (
    ValidationProfileName,
    XenoDreamInstallation,
    _mutex_name,
    managed_validation_session,
    resolve_xenodream_installation,
    resolve_profile_request,
    validation_profile,
)
from xenodream_xxp.errors import WorkspaceError


def test_validation_profiles_are_versioned_density_policies() -> None:
    preview = validation_profile(ValidationProfileName.PREVIEW)
    review = validation_profile(ValidationProfileName.REVIEW)

    assert (
        preview.name,
        preview.version,
        preview.mesh_size_percent,
        preview.timeout_seconds,
        preview.poll_seconds,
        preview.definition_sha256,
    ) == (
        ValidationProfileName.PREVIEW,
        1,
        10,
        180.0,
        1.0,
        "5a09d54fb8d003493a91ad3bc947412e82d123347fabd84e56d2d7f12bb3fbd7",
    )
    assert (
        review.name,
        review.version,
        review.mesh_size_percent,
        review.timeout_seconds,
        review.poll_seconds,
        review.definition_sha256,
    ) == (
        ValidationProfileName.REVIEW,
        1,
        50,
        600.0,
        1.0,
        "80c56205e309d7b12f834a7c8e0446570f37a47bfc998390c5779da7aa9af7b1",
    )


def test_profile_resolution_keeps_physical_size_outside_the_profile(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "xenodream_xxp.validation.resolve_xenodream_installation",
        lambda executable: type(
            "Installation",
            (),
            {
                "executable": str(executable),
                "file_version": "1.22.0.0",
                "executable_sha256": "1" * 64,
            },
        )(),
    )

    request = resolve_profile_request(
        ValidationProfileName.PREVIEW,
        stl_max_dimension_mm=120,
        executable="XenoDreamX.exe",
    )

    assert request.settings == MeshExportSettings(120, 10)
    assert request.timeout_seconds == 180.0
    assert request.poll_seconds == 1.0
    assert request.profile.name is ValidationProfileName.PREVIEW

    with pytest.raises(ValueError, match="between 10 and 10000"):
        resolve_profile_request(
            ValidationProfileName.PREVIEW,
            stl_max_dimension_mm=0,
            executable="XenoDreamX.exe",
        )


def test_installation_resolution_requires_the_supported_version_and_hash(
    tmp_path, monkeypatch
) -> None:
    executable = tmp_path / "XenoDreamX.exe"
    executable.write_bytes(b"pinned")
    monkeypatch.setattr(
        "xenodream_xxp.validation._file_version", lambda path: "1.22.0.0"
    )
    monkeypatch.setattr(
        "xenodream_xxp.validation._file_sha256",
        lambda path: "1674590ed60cea95cfeef076dfdafce4384fb86f118f087c42e23fd9429f1b6e",
    )

    installation = resolve_xenodream_installation(executable)
    assert installation.file_version == "1.22.0.0"

    monkeypatch.setattr(
        "xenodream_xxp.validation._file_sha256", lambda path: "0" * 64
    )
    with pytest.raises(WorkspaceError, match="does not match"):
        resolve_xenodream_installation(executable)

    monkeypatch.setattr(
        "xenodream_xxp.validation._file_version", lambda path: "5.0.0.0"
    )
    with pytest.raises(WorkspaceError, match="1.22.0.0 is required"):
        resolve_xenodream_installation(executable)


def test_managed_session_refuses_a_preexisting_xenodream_process(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "xenodream_xxp.validation._discover_xenodream_pids", lambda: (42, 84)
    )
    installation = XenoDreamInstallation("XenoDreamX.exe", "1.22.0.0", "1" * 64)

    with pytest.raises(WorkspaceError, match="42, 84"):
        with managed_validation_session(installation):
            pytest.fail("a preexisting session must prevent entry")


def test_mutex_identity_uses_the_windows_token_not_environment(monkeypatch) -> None:
    original = _mutex_name()
    monkeypatch.setenv("LOGNAME", "not-the-windows-user")
    monkeypatch.setenv("USERNAME", "also-not-the-windows-user")

    assert _mutex_name() == original
    assert original.startswith("Global\\XenoSculpt.XenoDream.Validation.")


def test_managed_session_refuses_a_second_process() -> None:
    installation = XenoDreamInstallation("unused", "1.22.0.0", "1" * 64)
    script = (
        "from xenodream_xxp.validation import managed_validation_session, "
        "XenoDreamInstallation; "
        "x=XenoDreamInstallation('unused','1.22.0.0','1'*64); "
        "managed_validation_session(x).__enter__()"
    )
    environment = dict(os.environ)
    environment["LOGNAME"] = "different-environment-name"
    with managed_validation_session(installation):
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).parents[1],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    assert result.returncode != 0
    assert "another XenoSculpt XenoDream validation is running" in result.stderr
