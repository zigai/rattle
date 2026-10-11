import sys
from contextlib import nullcontext
from pathlib import Path

import pytest

from rattle.util import append_sys_path


@pytest.mark.parametrize("already_present", [False, True])
@pytest.mark.parametrize("fail", [False, True])
def test_append_sys_path_restores_owned_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    already_present: bool,
    fail: bool,
) -> None:
    path = tmp_path / "rules"
    original = [*sys.path, path.as_posix()] if already_present else list(sys.path)
    monkeypatch.setattr(sys, "path", original.copy())
    expected = original if already_present else [*original, path.as_posix()]

    outcome = pytest.raises(RuntimeError, match="rule loading failed") if fail else nullcontext()
    with outcome, append_sys_path(path):
        assert sys.path == expected
        with append_sys_path(path):
            assert sys.path == expected
        assert sys.path == expected
        if fail:
            raise RuntimeError("rule loading failed")

    assert sys.path == original
