from __future__ import annotations

from pathlib import Path

import libcst as cst
from libcst.metadata import FilePathProvider

from rattle import Invalid, LintRule, RuleSetting, Valid
from rattle.rules.helpers import alias_name, dotted_name, is_excluded_path


class NoUnsafeTempfileFactories(LintRule):
    """Require tempfile context managers instead of unmanaged mkstemp or mkdtemp calls."""

    MESSAGE = "Use tempfile context managers instead of mkstemp or mkdtemp."
    SOURCE_PATTERNS = (b"tempfile",)
    TAGS = {"filesystem", "reliability"}
    METADATA_DEPENDENCIES = (*LintRule.METADATA_DEPENDENCIES, FilePathProvider)
    SETTINGS = {
        "excluded_path_parts": RuleSetting(list[str], default=["tests", "benchmarks"]),
    }

    VALID = [
        Valid(
            """
            import tempfile

            with tempfile.TemporaryDirectory() as path:
                use(path)
            """
        ),
        Valid(
            """
            from tempfile import NamedTemporaryFile

            with NamedTemporaryFile() as file:
                use(file.name)
            """
        ),
        Valid(
            """
            from tempfile import mkstemp

            factory().mkstemp()
            """
        ),
    ]

    INVALID = [
        Invalid(
            """
            import tempfile

            fd, path = tempfile.mkstemp()
            """,
            expected_message="Use tempfile context managers instead of mkstemp or mkdtemp.",
        ),
        Invalid(
            """
            from tempfile import mkdtemp as make_temp_dir

            path = make_temp_dir()
            """,
            expected_message="Use tempfile context managers instead of mkstemp or mkdtemp.",
        ),
    ]

    _BLOCKED_NAMES = frozenset({"mkdtemp", "mkstemp"})

    def __init__(self) -> None:
        super().__init__()

        self._tempfile_aliases: set[str] = set()
        self._factory_aliases: set[str] = set()
        self._current_file_path: Path | None = None

    def visit_Module(self, node: cst.Module) -> None:
        self._tempfile_aliases = {"tempfile"}
        self._factory_aliases = set()
        file_path = self.get_metadata(FilePathProvider, node)
        self._current_file_path = file_path if isinstance(file_path, Path) else None

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._tempfile_aliases = set()
        self._factory_aliases = set()
        self._current_file_path = None

    def visit_Import(self, node: cst.Import) -> None:
        if self._should_skip_current_file():
            return

        for import_alias in node.names:
            if not isinstance(import_alias.name, cst.Name):
                continue
            if import_alias.name.value != "tempfile":
                continue

            self._tempfile_aliases.add(alias_name(import_alias.asname, "tempfile"))

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if self._should_skip_current_file():
            return
        if dotted_name(node.module) != "tempfile":
            return
        if isinstance(node.names, cst.ImportStar):
            return

        for import_alias in node.names:
            if not isinstance(import_alias.name, cst.Name):
                continue
            if import_alias.name.value not in self._BLOCKED_NAMES:
                continue

            self._factory_aliases.add(alias_name(import_alias.asname, import_alias.name.value))

    def visit_Call(self, node: cst.Call) -> None:
        if self._should_skip_current_file():
            return

        name = dotted_name(node.func)
        if name in self._factory_aliases:
            self.report(node.func, self.MESSAGE)
            return
        if name is None or "." not in name:
            return

        module, function_name = name.rsplit(".", 1)
        if module in self._tempfile_aliases and function_name in self._BLOCKED_NAMES:
            self.report(node.func, self.MESSAGE)

    def _should_skip_current_file(self) -> bool:
        if self._current_file_path is None:
            return False

        return is_excluded_path(
            self._current_file_path,
            self.settings["excluded_path_parts"],
        )
