from __future__ import annotations

from pathlib import Path

import libcst as cst
from libcst.metadata import (
    FilePathProvider,
    PositionProvider,
    QualifiedName,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle import Invalid, LintRule, RuleSetting, Valid
from rattle.rules.helpers import (
    AssignmentAliasTracker,
    dotted_name,
    qualified_names_for_reaching_binding,
)


class NoUnsafeTempfileFactories(LintRule):
    """Require tempfile context managers instead of unmanaged mkstemp or mkdtemp calls."""

    MESSAGE = "Use tempfile context managers instead of mkstemp or mkdtemp."
    SOURCE_PATTERNS = (b"tempfile",)
    METADATA_DEPENDENCIES = (
        *LintRule.METADATA_DEPENDENCIES,
        FilePathProvider,
        PositionProvider,
        QualifiedNameProvider,
        ScopeProvider,
    )
    SETTINGS = {
        "excluded_path_parts": RuleSetting(
            list[str],
            default=["tests", "benchmarks"],
            description="Path components in which this rule is disabled.",
        ),
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
        Valid(
            """
            class tempfile:
                @staticmethod
                def mkstemp():
                    pass

            tempfile.mkstemp()
            """
        ),
        Valid(
            """
            import tempfile

            tempfile = fake
            tempfile.mkstemp()
            """
        ),
        Valid(
            """
            import tempfile

            def write_temp(tempfile):
                tempfile.mkstemp()
            """
        ),
        Valid(
            """
            from tempfile import mkstemp

            def write_temp(mkstemp):
                mkstemp()
            """
        ),
        Valid(
            """
            from tempfile import *

            def write_temp(mkstemp):
                mkstemp()
            """
        ),
        Valid(
            """
            import tempfile

            make_temp = tempfile.mkstemp

            def write_temp(make_temp):
                make_temp()
            """
        ),
        Valid(
            """
            import tempfile

            make_temp = tempfile.mkstemp

            def make_temp():
                pass

            make_temp()
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
        Invalid(
            """
            from tempfile import *

            fd, path = mkstemp()
            """,
            expected_message="Use tempfile context managers instead of mkstemp or mkdtemp.",
        ),
        Invalid(
            """
            from tempfile import mkstemp

            def write_temp():
                mkstemp = factory()
                mkstemp()

            fd, path = mkstemp()
            """,
            expected_message="Use tempfile context managers instead of mkstemp or mkdtemp.",
        ),
        Invalid(
            """
            import tempfile

            make_temp = tempfile.mkstemp
            fd, path = make_temp()
            """,
            expected_message="Use tempfile context managers instead of mkstemp or mkdtemp.",
        ),
        Invalid(
            """
            from tempfile import mkdtemp

            make_temp_dir = mkdtemp
            path = make_temp_dir()
            """,
            expected_message="Use tempfile context managers instead of mkstemp or mkdtemp.",
        ),
        Invalid(
            """
            from tempfile import mkdtemp

            make_temp_dir = other_make_temp_dir = mkdtemp
            path = other_make_temp_dir()
            """,
            expected_message="Use tempfile context managers instead of mkstemp or mkdtemp.",
        ),
    ]

    _BLOCKED_NAMES = frozenset({"mkdtemp", "mkstemp"})
    _QUALIFIED_BLOCKED_NAMES = frozenset(
        QualifiedName(name=f"tempfile.{name}", source=QualifiedNameSource.IMPORT)
        for name in _BLOCKED_NAMES
    )

    def __init__(self) -> None:
        super().__init__()

        self._has_tempfile_star_import = False
        self._aliases = AssignmentAliasTracker[str](self)
        self._current_file_path: Path | None = None

    def visit_Module(self, node: cst.Module) -> None:
        self._has_tempfile_star_import = False
        self._aliases.reset()
        file_path = self.get_metadata(FilePathProvider, node)
        self._current_file_path = file_path if isinstance(file_path, Path) else None

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._has_tempfile_star_import = False
        self._aliases.reset()
        self._current_file_path = None

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if self._should_skip_current_file():
            return
        if node.relative:
            return
        if dotted_name(node.module) != "tempfile":
            return
        if isinstance(node.names, cst.ImportStar):
            self._has_tempfile_star_import = True

    def visit_Assign(self, node: cst.Assign) -> None:
        if self._should_skip_current_file():
            return

        for assign_target in node.targets:
            self._record_alias(assign_target.target, node.value)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if self._should_skip_current_file() or node.value is None:
            return

        self._record_alias(node.target, node.value)

    def visit_NamedExpr(self, node: cst.NamedExpr) -> None:
        if self._should_skip_current_file():
            return

        self._record_alias(node.target, node.value)

    def visit_Call(self, node: cst.Call) -> None:
        if self._should_skip_current_file():
            return

        if (
            self._is_known_tempfile_factory(node.func)
            or self._is_factory_alias(node.func)
            or self._is_star_imported_factory(node.func)
        ):
            self.report(node.func, self.MESSAGE)

    def _is_known_tempfile_factory(self, expression: cst.BaseExpression) -> bool:
        if (
            isinstance(expression, cst.Attribute)
            and expression.attr.value in self._BLOCKED_NAMES
            and self._is_tempfile_module(expression.value)
        ):
            return True
        qualified_names = qualified_names_for_reaching_binding(self, expression)
        if any(
            qualified_name.source is QualifiedNameSource.LOCAL for qualified_name in qualified_names
        ):
            return False

        return any(
            qualified_name in self._QUALIFIED_BLOCKED_NAMES for qualified_name in qualified_names
        )

    def _is_factory_alias(self, expression: cst.BaseExpression) -> bool:
        return self._aliases.resolve(expression) == "factory"

    def _is_star_imported_factory(self, expression: cst.BaseExpression) -> bool:
        if not self._has_tempfile_star_import:
            return False
        if not isinstance(expression, cst.Name) or expression.value not in self._BLOCKED_NAMES:
            return False

        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        return not qualified_names

    def _record_alias(
        self,
        target: cst.BaseExpression,
        value: cst.BaseExpression,
    ) -> None:
        self._aliases.record(target, value, self._tempfile_alias_value)

    def _tempfile_alias_value(self, expression: cst.BaseExpression) -> str | None:
        if self._is_known_tempfile_factory(expression) or self._is_star_imported_factory(
            expression
        ):
            return "factory"
        qualified_names = qualified_names_for_reaching_binding(self, expression)
        if QualifiedName("tempfile", QualifiedNameSource.IMPORT) in qualified_names:
            return "module"
        return self._aliases.resolve(expression)

    def _is_tempfile_module(self, expression: cst.BaseExpression) -> bool:
        if isinstance(expression, cst.NamedExpr):
            return self._is_tempfile_module(expression.value)
        qualified_names = qualified_names_for_reaching_binding(self, expression)
        if QualifiedName("tempfile", QualifiedNameSource.IMPORT) in qualified_names:
            return True
        return self._aliases.resolve(expression) == "module"

    def _should_skip_current_file(self) -> bool:
        if self._current_file_path is None:
            return False

        excluded_parts = self.setting("excluded_path_parts", list[str])
        return any(part in excluded_parts for part in self._current_file_path.parts)
