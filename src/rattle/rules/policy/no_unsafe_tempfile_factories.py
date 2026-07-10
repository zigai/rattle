from __future__ import annotations

from collections.abc import Collection
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
from rattle.rules.helpers import dotted_name, is_excluded_path


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
        self._current_file_path: Path | None = None

    def visit_Module(self, node: cst.Module) -> None:
        self._has_tempfile_star_import = False
        self._factory_alias_nodes = set()
        file_path = self.get_metadata(FilePathProvider, node)
        self._current_file_path = file_path if isinstance(file_path, Path) else None

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._has_tempfile_star_import = False
        self._factory_alias_nodes = set()
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
        qualified_names = self._qualified_names_for_reaching_binding(expression)
        if any(
            qualified_name.source is QualifiedNameSource.LOCAL for qualified_name in qualified_names
        ):
            return False

        return any(
            qualified_name in self._QUALIFIED_BLOCKED_NAMES for qualified_name in qualified_names
        )

    def _qualified_names_for_reaching_binding(
        self,
        expression: cst.BaseExpression,
    ) -> Collection[QualifiedName]:
        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        root_name = expression
        while isinstance(root_name, cst.Attribute):
            root_name = root_name.value
        if not isinstance(root_name, cst.Name):
            return qualified_names

        binding_names = self._latest_same_scope_binding_names(root_name)
        if binding_names is None:
            return qualified_names

        expression_name = dotted_name(expression)
        if expression_name is None:
            return qualified_names
        _, _, suffix = expression_name.partition(".")
        if not suffix:
            return binding_names

        return {
            QualifiedName(name=f"{binding_name.name}.{suffix}", source=binding_name.source)
            for binding_name in binding_names
        }

    def _latest_same_scope_binding_names(
        self,
        root_name: cst.Name,
    ) -> Collection[QualifiedName] | None:
        scope = self.get_metadata(ScopeProvider, root_name, None)
        reference_position = self.get_metadata(PositionProvider, root_name, None)
        if scope is None or reference_position is None:
            return None

        try:
            assignments = scope[root_name.value]
        except KeyError:
            return None

        preceding_assignments = []
        for assignment in assignments:
            if assignment.scope is not scope:
                continue
            assignment_node = getattr(assignment, "node", None)
            if not isinstance(assignment_node, cst.CSTNode):
                continue
            assignment_position = self.get_metadata(PositionProvider, assignment_node, None)
            if assignment_position is None or (
                assignment_position.start.line,
                assignment_position.start.column,
            ) > (reference_position.start.line, reference_position.start.column):
                continue
            preceding_assignments.append(
                (
                    assignment_position.start.line,
                    assignment_position.start.column,
                    assignment,
                )
            )

        if not preceding_assignments:
            return None

        assignment = max(preceding_assignments, key=lambda item: item[:2])[2]
        return set(assignment.get_qualified_names_for(root_name.value))

    def _is_factory_alias(self, expression: cst.BaseExpression) -> bool:
        if not isinstance(expression, cst.Name):
            return False

        scope = self.get_metadata(ScopeProvider, expression, None)
        if scope is None:
            return False

        try:
            assignments = scope[expression.value]
        except KeyError:
            return False

        reference_position = self.get_metadata(PositionProvider, expression, None)
        if reference_position is None:
            return False

        preceding_assignments: list[tuple[int, int, cst.CSTNode]] = []
        for assignment in assignments:
            assignment_node = getattr(assignment, "node", None)
            if not isinstance(assignment_node, cst.CSTNode):
                continue
            assignment_position = self.get_metadata(PositionProvider, assignment_node, None)
            if assignment_position is None or (
                assignment_position.start.line,
                assignment_position.start.column,
            ) > (reference_position.start.line, reference_position.start.column):
                continue
            preceding_assignments.append(
                (
                    assignment_position.start.line,
                    assignment_position.start.column,
                    assignment_node,
                )
            )

        if not preceding_assignments:
            return False

        assignment_node = max(preceding_assignments, key=lambda item: item[:2])[2]
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
        if isinstance(target, cst.List | cst.Tuple) and isinstance(value, cst.List | cst.Tuple):
            if len(target.elements) != len(value.elements):
                return
            for target_element, value_element in zip(target.elements, value.elements, strict=True):
                self._record_factory_alias(target_element.value, value_element.value)
            return

        if not isinstance(target, cst.Name):
            return

        if self._is_known_tempfile_factory(value) or self._is_factory_alias(value):
            self._factory_alias_nodes.add(target)
            return

        self._factory_alias_nodes.discard(target)

    def _should_skip_current_file(self) -> bool:
        if self._current_file_path is None:
            return False

        return is_excluded_path(
            self._current_file_path,
            self.setting("excluded_path_parts", list[str]),
        )
