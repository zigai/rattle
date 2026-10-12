from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from rattle.cli.environment import _project_rattle_for_reexec

EXECUTABLE = Path("Scripts/rattle.exe") if os.name == "nt" else Path("bin/rattle")


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RATTLE_UV_RUN_REEXEC", raising=False)
    monkeypatch.delenv("RATTLE_NO_UV_RUN_REEXEC", raising=False)
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "global-tool"))
    return tmp_path


def install_rattle(environment: Path) -> Path:
    executable = environment / EXECUTABLE
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")
    return executable


def test_hands_off_to_rattle_installed_in_project_environment(project: Path) -> None:
    executable = install_rattle(project / ".venv")

    assert _project_rattle_for_reexec(["lint", "."]) == executable


def test_stays_in_process_when_already_running_in_project_environment(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_rattle(project / ".venv")
    monkeypatch.setattr(sys, "prefix", str(project / ".venv"))

    assert _project_rattle_for_reexec(["lint", "."]) is None


def test_stays_in_process_when_project_environment_lacks_rattle(project: Path) -> None:
    (project / ".venv").mkdir()

    assert _project_rattle_for_reexec(["lint", "."]) is None


@pytest.mark.parametrize("configured", ["envs/ci", "absolute"])
def test_uses_configured_project_environment(
    project: Path, monkeypatch: pytest.MonkeyPatch, configured: str
) -> None:
    environment = project / "envs" / "ci" if configured == "envs/ci" else project / "elsewhere"
    monkeypatch.setenv(
        "UV_PROJECT_ENVIRONMENT", configured if configured == "envs/ci" else str(environment)
    )
    executable = install_rattle(environment)
    install_rattle(project / ".venv")

    assert _project_rattle_for_reexec(["lint", "."]) == executable


def test_stays_in_process_after_handoff(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_rattle(project / ".venv")
    monkeypatch.setenv("RATTLE_UV_RUN_REEXEC", "1")

    assert _project_rattle_for_reexec(["lint", "."]) is None
