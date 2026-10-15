from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("marker", "configured"),
    [
        pytest.param("lock", None, id="uv-lock"),
        pytest.param("tool", None, id="uv-tool"),
        pytest.param("groups", None, id="dependency-groups"),
        pytest.param("lock", "envs/runtime", id="relative-environment"),
        pytest.param("lock", "absolute", id="absolute-environment"),
    ],
)
def test_check_uses_invoked_installation_despite_project_environment(
    tmp_path: Path, marker: str, configured: str | None
) -> None:
    config = '[tool.rattle]\nroot=true\nenable=["no-redundant-f-string"]\n'
    if marker == "lock":
        (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    elif marker == "tool":
        config += "[tool.uv]\n"
    else:
        config += "[dependency-groups]\ntest=[]\n"
    (tmp_path / "pyproject.toml").write_text(config, encoding="utf-8")
    path = tmp_path / "sample.py"
    source = 'value = f"text"\n'
    path.write_text(source, encoding="utf-8")
    environment = os.environ | {"RATTLE_DISABLE_CACHE": "1"}
    environment.pop("UV_PROJECT_ENVIRONMENT", None)
    if configured == "absolute":
        project_environment = tmp_path / "runtime"
        environment["UV_PROJECT_ENVIRONMENT"] = str(project_environment)
    elif configured is not None:
        project_environment = tmp_path / configured
        environment["UV_PROJECT_ENVIRONMENT"] = configured
    else:
        project_environment = tmp_path / ".venv"
    executable = project_environment / ("Scripts/rattle.exe" if os.name == "nt" else "bin/rattle")
    executable.parent.mkdir(parents=True)
    shutil.copy2(Path(sys.executable).resolve(), executable)

    result = subprocess.run(
        [sys.executable, "-m", "rattle", "check", "--json", path.as_posix()],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1, result.stderr
    assert [diagnostic["rule"] for diagnostic in json.loads(result.stdout)] == [
        "no-redundant-f-string"
    ]
    assert path.read_text(encoding="utf-8") == source


def test_local_rules_import_dependencies_in_invoked_interpreter(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.rattle]\nroot=true\nenable=[".rules"]\n', encoding="utf-8"
    )
    (tmp_path / "settings.py").write_text('MESSAGE = "Use another name"\n', encoding="utf-8")
    (tmp_path / "rules.py").write_text(
        "import sys\n"
        "from rattle import LintRule\n"
        "from .settings import MESSAGE\n"
        "class NameCheck(LintRule):\n"
        "    def visit_Name(self, node):\n"
        "        if node.value == 'blocked':\n"
        "            self.report(node, f'{MESSAGE}: {sys.executable}')\n",
        encoding="utf-8",
    )
    path = tmp_path / "sample.py"
    path.write_text("blocked = 0\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "rattle", "check", "--json", path.as_posix()],
        cwd=tmp_path,
        env=os.environ | {"RATTLE_DISABLE_CACHE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1, result.stderr
    assert [diagnostic["message"] for diagnostic in json.loads(result.stdout)] == [
        f"Use another name: {sys.executable}"
    ]


@pytest.mark.parametrize(
    ("arguments", "expected_exit"),
    [
        pytest.param(["check", "--rules", ".rules", "sample.py"], 2, id="explicit-rule"),
        pytest.param(["validate", "pyproject.toml"], 1, id="validation"),
        pytest.param(["rules"], 0, id="non-strict-listing"),
    ],
)
def test_rule_dependency_errors_identify_invoked_interpreter(
    tmp_path: Path, arguments: list[str], expected_exit: int
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.rattle]\nroot=true\nenable=[".rules"]\n', encoding="utf-8"
    )
    (tmp_path / "rules.py").write_text("import missing_rule_dependency\n", encoding="utf-8")
    (tmp_path / "sample.py").write_text("value = 0\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "rattle", *arguments],
        cwd=tmp_path,
        env=os.environ | {"RATTLE_DISABLE_CACHE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == expected_exit, result.stderr
    assert "Dependency module 'missing_rule_dependency' was not found" in result.stderr
    assert f"Python interpreter: {sys.executable}" in result.stderr
    assert "dependencies" in result.stderr
    assert "environment" in result.stderr
