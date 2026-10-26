import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from rattle.api import rattle_paths
from rattle.config.models import Config
from rattle.diagnostics import FileContent, Result
from rattle.rule import LintRule


class TestApi:
    @pytest.mark.parametrize("target_kind", ["directory", "file", "loop", "missing", "self"])
    def test_directory_discovery_skips_external_or_cyclic_links(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target_kind: str
    ) -> None:
        project = tmp_path / "project"
        project.mkdir()
        (project / "pyproject.toml").write_text(
            "[tool.rattle]\nroot = true\nenable = ['modernization']\n"
        )
        local = project / "local.py"
        local.write_text("pass\n")
        external = tmp_path / "external"
        external.mkdir()
        foreign = external / "foreign.py"
        foreign.write_text("pass\n")
        targets = {
            "directory": external,
            "file": foreign,
            "loop": project,
            "missing": external / "missing",
            "self": project / "linked.py",
        }
        (project / "linked.py").symlink_to(
            targets[target_kind], target_is_directory=target_kind in {"directory", "loop"}
        )
        monkeypatch.setenv("RATTLE_CACHE_DIR", str(tmp_path / "cache"))

        results = list(rattle_paths([project], parallel=False))

        assert [result.path for result in results] == [local]
        assert foreign.read_text() == "pass\n"

    @pytest.mark.parametrize(
        ("link_name", "target_name"),
        [("linked.py", "shared/source.py"), ("linked", "shared")],
    )
    def test_directory_discovery_fixes_internal_symlink_targets(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, link_name: str, target_name: str
    ) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[tool.rattle]\nroot = true\nformatter = 'none'\nenable = ['no-redundant-f-string']\n"
        )
        shared = tmp_path / "shared"
        shared.mkdir()
        source = shared / "source.py"
        source.write_text("value = f'example'\n")
        package = tmp_path / "package"
        package.mkdir()
        (package / link_name).symlink_to(
            tmp_path / target_name, target_is_directory=target_name == "shared"
        )
        monkeypatch.setenv("RATTLE_CACHE_DIR", str(tmp_path / "cache"))

        results = list(rattle_paths([package], autofix=True, parallel=False))

        assert [result.path for result in results] == [source]
        assert source.read_text() == "value = 'example'\n"

    def test_explicit_symlink_file_is_checked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[tool.rattle]\nroot = true\nenable = ['modernization']\n"
        )
        source = tmp_path / "source.py"
        source.write_text("pass\n")
        link = tmp_path / "linked.py"
        link.symlink_to(source)
        monkeypatch.setenv("RATTLE_CACHE_DIR", str(tmp_path / "cache"))

        results = list(rattle_paths([link], parallel=False))

        assert [result.path for result in results] == [source]

    def test_directory_discovery_preserves_gitignore_rules(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[tool.rattle]\nroot = true\nenable = ['modernization']\n"
        )
        (tmp_path / ".gitignore").write_text("ignored.py\nignored_dir/\n")
        local = tmp_path / "local.py"
        local.write_text("pass\n")
        (tmp_path / "ignored.py").write_text("pass\n")
        ignored = tmp_path / "ignored_dir"
        ignored.mkdir()
        (ignored / "other.py").write_text("pass\n")
        (tmp_path / "linked.py").symlink_to(tmp_path / "ignored.py")
        (tmp_path / "linked_dir").symlink_to(ignored, target_is_directory=True)
        nested = tmp_path / "nested"
        nested.mkdir()
        stub = nested / "source.pyi"
        stub.write_text("value: int\n")
        monkeypatch.setenv("RATTLE_CACHE_DIR", str(tmp_path / "cache"))

        results = list(rattle_paths([tmp_path], parallel=False))

        assert sorted(result.path for result in results) == [local, stub]

    def test_rattle_paths_clean_status_cache_skips_source_read(self, tmp_path: Path) -> None:
        root = tmp_path
        paths = []
        for index in range(20):
            path = root / f"clean_{index}.py"
            path.write_bytes(f"value = {index}\n".encode())
            paths.append(path)
        cache_dir = root / "cache"
        (root / "pyproject.toml").write_text(
            "[tool.rattle]\nroot = true\nenable = ['modernization']\n"
        )

        with patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}):
            list(rattle_paths(paths, parallel=False))
            with (
                patch("rattle.execution.paths.generate_config") as generate_config,
                patch("rattle.execution.content.LintRunner") as lint_runner,
            ):
                results = list(rattle_paths(paths, parallel=False))

        assert [result.source for result in results] == [None for _ in range(20)]
        generate_config.assert_not_called()
        lint_runner.assert_not_called()

    def test_rattle_paths_result_cache_lookup_is_single_owner(self, tmp_path: Path) -> None:
        root = tmp_path
        path = root / "clean.py"
        path.write_bytes(b"pass\n")
        cache_dir = root / "cache"
        config = Config(path=path, root=root)

        with (
            patch.dict(os.environ, {"RATTLE_CACHE_DIR": cache_dir.as_posix()}),
            patch("rattle.execution.paths.generate_config", return_value=config),
            patch("rattle.cache.ResultCache._read_result", return_value=None) as read_result,
        ):
            list(rattle_paths([path], parallel=False))

        read_result.assert_called_once()

    def test_rattle_paths_batches_ruff_format_after_automatic_fixes(
        self,
        tmp_path: Path,
    ) -> None:
        class FixRule(LintRule):
            pass

        def rattle_bytes_stub(
            path: Path,
            content: FileContent,
            *,
            config: Config,
            **_kwargs: object,
        ) -> Generator[Result, bool, FileContent | None]:
            seen_formatters.append(config.formatter)
            yield Result(path, violation=None, source=content, config=config)
            return b"y\n"

        first = tmp_path / "first.py"
        second = tmp_path / "second.py"
        first.write_text("x\n")
        second.write_text("x\n")
        config = Config(path=tmp_path, root=tmp_path, formatter="ruff")
        seen_formatters: list[str | None] = []

        with (
            patch("rattle.execution.paths.generate_config", return_value=config),
            patch(
                "rattle.execution.files.collect_rules",
                return_value=(FixRule(),),
            ),
            patch("rattle.execution.files.rattle_bytes", side_effect=rattle_bytes_stub),
            patch("rattle.execution.paths.format_paths") as format_paths,
        ):
            list(rattle_paths([first, second], autofix=True, parallel=False))

        assert first.read_text() == "y\n"
        assert second.read_text() == "y\n"
        assert seen_formatters == [None, None]
        format_paths.assert_called_once()
        formatted_paths, batch_config = format_paths.call_args.args
        assert formatted_paths == [first.resolve(), second.resolve()]
        assert batch_config.formatter == "ruff"
