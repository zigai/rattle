from __future__ import annotations

import importlib
import importlib.metadata

version_module = importlib.import_module("rattle.__version__")


def test_version_prefers_rattle_lint_distribution(monkeypatch) -> None:
    calls: list[str] = []

    def fake_version(name: str) -> str:
        calls.append(name)
        if name == "rattle-lint":
            return "1.0.2"
        raise importlib.metadata.PackageNotFoundError

    with monkeypatch.context() as m:
        m.setattr(importlib.metadata, "version", fake_version)
        reloaded = importlib.reload(version_module)

        assert reloaded.__version__ == "1.0.2"
        assert calls == ["rattle-lint"]

    importlib.reload(version_module)


def test_version_returns_unknown_when_distribution_is_not_installed(
    monkeypatch,
) -> None:
    calls: list[str] = []

    def fake_version(name: str) -> str:
        calls.append(name)
        raise importlib.metadata.PackageNotFoundError

    with monkeypatch.context() as m:
        m.setattr(importlib.metadata, "version", fake_version)
        reloaded = importlib.reload(version_module)

        assert reloaded.__version__ == "0+unknown"
        assert calls == ["rattle-lint"]

    importlib.reload(version_module)
