from __future__ import annotations

from pathlib import Path

import libcst as cst
from libcst.metadata import (
    FilePathProvider,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle.rule import Invalid, LintRule, RuleSetting, Valid
from rattle.rules.helpers import (
    TRANSPARENT_ANNOTATION_ARGUMENTS,
    is_excluded_path,
    single_assignment_node,
    subscript_arguments,
)


class _AliasCollector(cst.CSTVisitor):
    def __init__(self, resolver: _AnyResolver) -> None:
        self._resolver = resolver

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if (
            isinstance(node.target, cst.Name)
            and node.value is not None
            and self._resolver.is_type_alias_marker(node.annotation.annotation)
        ):
            self._resolver.record_alias((node, node.target), node.value)

    def visit_TypeAlias(self, node: cst.TypeAlias) -> None:
        self._resolver.record_alias((node, node.name), node.value)


class _AnyResolver:
    """Resolve local type aliases whose complete meaning is ``typing.Any``."""

    def __init__(self, rule: LintRule) -> None:
        self._rule = rule
        self._aliases: dict[cst.CSTNode, cst.BaseExpression] = {}

    def reset(self) -> None:
        self._aliases = {}

    def collect(self, module: cst.Module) -> None:
        module.visit(_AliasCollector(self))

    def record_alias(
        self,
        nodes: tuple[cst.CSTNode, ...],
        value: cst.BaseExpression,
    ) -> None:
        for node in nodes:
            self._aliases[node] = value

    def is_type_alias_marker(self, expression: cst.BaseExpression) -> bool:
        return self._qualified_name(expression) in {
            "typing.TypeAlias",
            "typing_extensions.TypeAlias",
        }

    def resolves_to_any(self, expression: cst.BaseExpression) -> bool:
        return self._resolves_to_any(expression, frozenset())

    def _resolves_to_any(  # noqa: PLR0911 - flat recursive type grammar
        self,
        expression: cst.BaseExpression,
        resolving: frozenset[cst.CSTNode],
    ) -> bool:
        alias = self._resolve_alias(expression)
        if alias is not None:
            alias_node, alias_value = alias
            if alias_node in resolving:
                return False
            return self._resolves_to_any(alias_value, resolving | {alias_node})

        if self._qualified_name(expression) == "typing.Any":
            return True

        if isinstance(expression, cst.BinaryOperation) and isinstance(
            expression.operator, cst.BitOr
        ):
            return self._resolves_to_any(expression.left, resolving) or self._resolves_to_any(
                expression.right, resolving
            )

        if not isinstance(expression, cst.Subscript):
            return False

        arguments = subscript_arguments(expression)
        if arguments is None:
            return False
        qualified_name = self._qualified_name(expression.value)
        positions = (
            TRANSPARENT_ANNOTATION_ARGUMENTS.get(qualified_name)
            if qualified_name is not None
            else None
        )
        if positions is None and qualified_name not in TRANSPARENT_ANNOTATION_ARGUMENTS:
            return False
        selected_positions = range(len(arguments)) if positions is None else positions
        return any(
            position < len(arguments) and self._resolves_to_any(arguments[position], resolving)
            for position in selected_positions
        )

    def _resolve_alias(
        self, expression: cst.BaseExpression
    ) -> tuple[cst.CSTNode, cst.BaseExpression] | None:
        if not isinstance(expression, cst.Name):
            return None
        assignment_node = single_assignment_node(self._rule, expression)
        if assignment_node is None:
            return None
        alias_value = self._aliases.get(assignment_node)
        if alias_value is None:
            return None
        return assignment_node, alias_value

    def _qualified_name(self, expression: cst.BaseExpression) -> str | None:
        qualified_names = self._rule.get_metadata(QualifiedNameProvider, expression, set())
        if any(name.source is QualifiedNameSource.LOCAL for name in qualified_names):
            return None
        names = {
            name.name
            for name in qualified_names
            if name.source in {QualifiedNameSource.BUILTIN, QualifiedNameSource.IMPORT}
        }
        return next(iter(names)) if len(names) == 1 else None


class NoAnyTypeAliases(LintRule):
    """Disallow explicit type aliases whose complete meaning is ``Any``."""

    MESSAGE = "Do not hide `Any` behind a type alias; use a concrete owner type."
    METADATA_DEPENDENCIES = (
        *LintRule.METADATA_DEPENDENCIES,
        FilePathProvider,
        QualifiedNameProvider,
        ScopeProvider,
    )
    SETTINGS = {
        "excluded_path_parts": RuleSetting(
            list[str],
            default=["tests"],
            description=(
                "Skip files whose path contains any of these components, in addition to "
                "files named test_*.py."
            ),
        ),
    }

    VALID = [
        Valid("""
            from typing import Any, TypeAlias

            Rows: TypeAlias = list[Any]
            """),
        Valid("""
            from typing import Any as ImportedAny, TypeAlias

            class ImportedAny:
                pass

            Value: TypeAlias = ImportedAny
            """),
    ]
    INVALID = [
        Invalid(
            """
            from typing import Any

            type Payload = Any
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            from typing import Annotated, Any, TypeAlias

            Dynamic: TypeAlias = Any
            Payload: TypeAlias = Annotated[Dynamic, "external"]
            """,
            expected_message=MESSAGE,
        ),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._current_file_path: Path | None = None
        self._resolver = _AnyResolver(self)

    def visit_Module(self, node: cst.Module) -> None:
        file_path = self.get_metadata(FilePathProvider, node)
        self._current_file_path = file_path if isinstance(file_path, Path) else None
        self._resolver.reset()
        self._resolver.collect(node)

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node
        self._current_file_path = None
        self._resolver.reset()

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if (
            self._should_skip_current_file()
            or not isinstance(node.target, cst.Name)
            or node.value is None
            or not self._resolver.is_type_alias_marker(node.annotation.annotation)
            or not self._resolver.resolves_to_any(node.value)
        ):
            return
        self.report(node.target, self.MESSAGE)

    def visit_TypeAlias(self, node: cst.TypeAlias) -> None:
        if self._should_skip_current_file() or not self._resolver.resolves_to_any(node.value):
            return
        self.report(node.name, self.MESSAGE)

    def _should_skip_current_file(self) -> bool:
        if self._current_file_path is None:
            return False
        return is_excluded_path(
            self._current_file_path,
            self.setting("excluded_path_parts", list[str]),
        )
