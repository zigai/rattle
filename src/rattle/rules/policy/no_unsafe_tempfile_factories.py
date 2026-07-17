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
    assignment_leaf_pairs,
    dotted_name,
    latest_assignment_node,
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
        self._factory_alias_nodes: set[cst.CSTNode] = set()
        self._tempfile_module_alias_nodes: set[cst.CSTNode] = set()
        self._current_file_path: Path | None = None

    def visit_Module(self, node: cst.Module) -> None:
        self._has_tempfile_star_import = False
        self._factory_alias_nodes = set()
        self._tempfile_module_alias_nodes = set()
        file_path = self.get_metadata(FilePathProvider, node)
        self._current_file_path = file_path if isinstance(file_path, Path) else None

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._has_tempfile_star_import = False
        self._factory_alias_nodes = set()
        self._tempfile_module_alias_nodes = set()
        self._current_file_path = None

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if self._should_skip_current_file():
            return
        if dotted_name(node.module) != "tempfile":
            return
        if isinstance(node.names, cst.ImportStar):
            self._has_tempfile_star_import = True

    def visit_Assign(self, node: cst.Assign) -> None:
        if self._should_skip_current_file():
            return

        for assign_target in node.targets:
            self._record_tempfile_module_alias(assign_target.target, node.value)
            self._record_factory_alias(assign_target.target, node.value)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if self._should_skip_current_file() or node.value is None:
            return

        self._record_factory_alias(node.target, node.value)

    def visit_NamedExpr(self, node: cst.NamedExpr) -> None:
        if self._should_skip_current_file():
            return

        self._record_factory_alias(node.target, node.value)

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
        assignment_node = latest_assignment_node(self, expression)
        return assignment_node in self._factory_alias_nodes

    def _is_star_imported_factory(self, expression: cst.BaseExpression) -> bool:
        if not self._has_tempfile_star_import:
            return False
        if not isinstance(expression, cst.Name) or expression.value not in self._BLOCKED_NAMES:
            return False

        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        return not qualified_names

    def _record_factory_alias(
        self,
        target: cst.BaseExpression,
        value: cst.BaseExpression,
    ) -> None:
        for leaf_target, leaf_value in assignment_leaf_pairs(target, value):
            if not isinstance(leaf_target, cst.Name):
                continue

            if (
                self._is_known_tempfile_factory(leaf_value)
                or self._is_factory_alias(leaf_value)
                or self._is_star_imported_factory(leaf_value)
            ):
                self._factory_alias_nodes.add(leaf_target)
                continue

            self._factory_alias_nodes.discard(leaf_target)

    def _record_tempfile_module_alias(
        self, target: cst.BaseExpression, value: cst.BaseExpression
    ) -> None:
        if not isinstance(target, cst.Name):
            return
        if self._is_tempfile_module(value):
            self._tempfile_module_alias_nodes.add(target)
        else:
            self._tempfile_module_alias_nodes.discard(target)

    def _is_tempfile_module(self, expression: cst.BaseExpression) -> bool:
        qualified_names = qualified_names_for_reaching_binding(self, expression)
        if QualifiedName("tempfile", QualifiedNameSource.IMPORT) in qualified_names:
            return True
        assignment_node = latest_assignment_node(self, expression)
        return assignment_node in self._tempfile_module_alias_nodes

    def _should_skip_current_file(self) -> bool:
        if self._current_file_path is None:
            return False

        excluded_parts = self.setting("excluded_path_parts", list[str])
        return any(part in excluded_parts for part in self._current_file_path.parts)
