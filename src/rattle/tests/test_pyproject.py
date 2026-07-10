import os
from pathlib import Path

from rattle.pyproject import load_pyproject


def test_load_pyproject_reuses_parse_until_file_metadata_changes(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text("[tool.example]\nvalue = 1\n")

    first = load_pyproject(path)
    second = load_pyproject(path)

    assert second is first

    first_stat = path.stat()
    path.write_text("[tool.example]\nvalue = 2\n")
    os.utime(
        path,
        ns=(first_stat.st_atime_ns, first_stat.st_mtime_ns + 1_000_000_000),
    )

    updated = load_pyproject(path)

    assert updated is not first
    assert updated["tool"] == {"example": {"value": 2}}
