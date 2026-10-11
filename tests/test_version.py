from __future__ import annotations

import importlib
import importlib.metadata

import pytest

version_module = importlib.import_module("rattle.__version__")


@pytest.mark.parametrize(
    ("installed_version", "expected"),
    [
        pytest.param("1.0.2", "1.0.2", id="installed"),
        pytest.param(None, "0+unknown", id="missing"),
    ],
)
def test_version_uses_distribution_metadata(
    monkeypatch: pytest.MonkeyPatch, installed_version: str | None, expected: str
) -> None:
    calls: list[str] = []

    def fake_version(name: str) -> str:
        calls.append(name)
        if name == "rattle-lint" and installed_version is not None:
            return installed_version
        raise importlib.metadata.PackageNotFoundError

    with monkeypatch.context() as context:
        context.setattr(importlib.metadata, "version", fake_version)
        reloaded = importlib.reload(version_module)

        assert reloaded.__version__ == expected
        assert calls == ["rattle-lint"]

    importlib.reload(version_module)
