from __future__ import annotations

from pathlib import Path

import libcst as cst
from libcst.metadata import (
    FilePathProvider,
    QualifiedNameProvider,
    ScopeProvider,
)

from rattle.rule import Invalid, LintRule, RuleSetting, Valid
from rattle.rules.helpers import is_excluded_path, single_assignment_node
from rattle.rules.typing.no_any_type_aliases import _AnyResolver

_DIRECT_EVIDENCE_NODES = (
    cst.BaseNumber,
    cst.Call,
    cst.ConcatenatedString,
    cst.Dict,
    cst.DictComp,
    cst.FormattedString,
    cst.GeneratorExp,
    cst.Lambda,
    cst.List,
    cst.ListComp,
    cst.Set,
    cst.SetComp,
    cst.SimpleString,
    cst.Tuple,
)


class _InitializerCollector(cst.CSTVisitor):
    def __init__(self) -> None:
        self.initializers: dict[cst.CSTNode, cst.BaseExpression] = {}

    def visit_Assign(self, node: cst.Assign) -> None:
        if len(node.targets) != 1 or not isinstance(node.targets[0].target, cst.Name):
            return
        target = node.targets[0].target
        self.initializers[node] = node.value
        self.initializers[target] = node.value

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if not isinstance(node.target, cst.Name) or node.value is None:
            return
        self.initializers[node] = node.value
        self.initializers[node.target] = node.value


class NoKnownValueToAny(LintRule):
    """Disallow direct ``Any`` annotations that erase syntactically known evidence."""

    MESSAGE = (
        "This explicit `Any` annotation discards known type evidence. Keep inference or use "
        "a concrete owner contract."
    )
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
            from typing import Any

            pending: Any
            placeholder: Any = None
            supplied: Any = value
            """),
        Valid("""
            from typing import Any

            values: list[Any] = []
            """),
        Valid("""
            class Any:
                pass

            value: Any = make_value()
            """),
    ]
    INVALID = [
        Invalid(
            """
            from typing import Any

            payload: Any = {"ready": True}
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            from typing import Any

            created = build_payload()
            self.payload: Any = created
            """,
            expected_message=MESSAGE,
        ),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._current_file_path: Path | None = None
        self._resolver = _AnyResolver(self)
        self._initializers: dict[cst.CSTNode, cst.BaseExpression] = {}

    def visit_Module(self, node: cst.Module) -> None:
        file_path = self.get_metadata(FilePathProvider, node)
        self._current_file_path = file_path if isinstance(file_path, Path) else None
        self._resolver.reset()
        self._resolver.collect(node)
        collector = _InitializerCollector()
        node.visit(collector)
        self._initializers = collector.initializers

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node
        self._current_file_path = None
        self._resolver.reset()
        self._initializers = {}

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if (
            self._should_skip_current_file()
            or node.value is None
            or not isinstance(node.target, cst.Name | cst.Attribute)
            or not self._resolver.resolves_to_any(node.annotation.annotation)
            or not self._has_known_evidence(node.value)
        ):
            return
        self.report(node.annotation, self.MESSAGE)

    def _has_known_evidence(self, expression: cst.BaseExpression) -> bool:
        if isinstance(expression, cst.Name):
            if expression.value in {"None", "Ellipsis"}:
                return False
            if expression.value in {"False", "True"}:
                return True
            assignment_node = single_assignment_node(self, expression)
            if assignment_node is None:
                return False
            initializer = self._initializers.get(assignment_node)
            return initializer is not None and self._is_direct_evidence(initializer)

        return self._is_direct_evidence(expression)

    @staticmethod
    def _is_direct_evidence(expression: cst.BaseExpression) -> bool:
        if isinstance(expression, cst.Ellipsis):
            return False
        if isinstance(expression, cst.Name):
            return expression.value in {"False", "True"}
        if isinstance(expression, cst.UnaryOperation):
            return isinstance(expression.operator, cst.Minus | cst.Plus) and isinstance(
                expression.expression, cst.BaseNumber
            )
        return isinstance(expression, _DIRECT_EVIDENCE_NODES)

    def _should_skip_current_file(self) -> bool:
        if self._current_file_path is None:
            return False
        return is_excluded_path(
            self._current_file_path,
            self.setting("excluded_path_parts", list[str]),
        )
