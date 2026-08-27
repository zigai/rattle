from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import libcst as cst
from libcst.metadata import FilePathProvider, ParentNodeProvider

from rattle.rule import Invalid, RuleSetting, Valid
from rattle.rules.helpers import is_excluded_path, latest_assignment, subscript_arguments
from rattle.rules.typing import _cast_annotations

_DIRECT_BROAD_NAMES = {"builtins.object", "typing.Any"}
_OPEN_MAPPING_NAMES = {
    "builtins.dict",
    "collections.ChainMap",
    "collections.OrderedDict",
    "collections.defaultdict",
    "collections.abc.Mapping",
    "collections.abc.MutableMapping",
    "typing.ChainMap",
    "typing.DefaultDict",
    "typing.Dict",
    "typing.Mapping",
    "typing.MutableMapping",
    "typing.OrderedDict",
}


@dataclass(frozen=True)
class _BroadAnnotation:
    arguments: tuple[cst.BaseExpression, ...] = ()


class NoWidenThenCast(_cast_annotations.CastAnnotationRule):
    """Disallow discarding local type evidence and recovering it with a later cast."""

    MESSAGE = (
        "This value was widened and then cast back to a narrower type. Preserve its "
        "original type evidence."
    )
    METADATA_DEPENDENCIES = (
        *_cast_annotations.CastAnnotationRule.METADATA_DEPENDENCIES,
        FilePathProvider,
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
        Valid(
            """
            from typing import cast

            value: object = source
            value = replacement
            result = cast(str, value)
            """
        ),
        Valid(
            """
            from typing import cast

            def convert(value: object) -> str:
                return cast(str, value)
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            from typing import cast

            precise: str = "value"
            widened: object = precise
            result = cast(str, widened)
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            from collections.abc import Mapping
            from typing import Any, cast

            precise: dict[str, int] = {"answer": 42}
            widened: Mapping[str, Any] = precise
            result = cast(dict[str, int], widened)
            """,
            expected_message=MESSAGE,
        ),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._current_file_path: Path | None = None
        self._widenings: dict[cst.CSTNode, _BroadAnnotation] = {}

    def visit_Module(self, node: cst.Module) -> None:
        super().visit_Module(node)
        file_path = self.get_metadata(FilePathProvider, node)
        self._current_file_path = file_path if isinstance(file_path, Path) else None
        self._widenings = {}

    def leave_Module(self, original_node: cst.Module) -> None:
        self._current_file_path = None
        self._widenings = {}
        super().leave_Module(original_node)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if self._should_skip_current_file() or not isinstance(node.target, cst.Name):
            return
        if node.value is None or isinstance(node.value, cst.Ellipsis):
            return
        if not self._is_unconditional_scope_binding(node):
            return

        broad_annotation = self._broad_annotation(node.annotation.annotation)
        if broad_annotation is not None:
            self._widenings[node.target] = broad_annotation

    def visit_Call(self, node: cst.Call) -> None:
        if self._should_skip_current_file():
            return

        cast_arguments = self.cast_arguments(node)
        if cast_arguments is None:
            return
        target, value = cast_arguments
        if not isinstance(value, cst.Name):
            return

        assignment = latest_assignment(self, value, same_scope_only=True)
        if assignment is None:
            return
        broad_annotation = self._widenings.get(assignment.node)
        if broad_annotation is None or not self._is_narrower_target(target, broad_annotation):
            return

        self.report(value, self.MESSAGE)

    def _broad_annotation(self, expression: cst.BaseExpression) -> _BroadAnnotation | None:
        qualified_name = self._resolved_type_name(expression)
        if qualified_name in _DIRECT_BROAD_NAMES:
            return _BroadAnnotation()

        if not isinstance(expression, cst.Subscript):
            return None
        mapping_name = self._resolved_type_name(expression.value)
        if mapping_name not in _OPEN_MAPPING_NAMES:
            return None
        arguments = subscript_arguments(expression)
        if arguments is None or len(arguments) != 2:
            return None
        if self._resolved_type_name(arguments[1]) not in _DIRECT_BROAD_NAMES:
            return None
        return _BroadAnnotation(tuple(arguments))

    def _is_narrower_target(
        self,
        target: cst.BaseExpression,
        broad_annotation: _BroadAnnotation,
    ) -> bool:
        if self._contains_broad_type(target):
            return False
        if not broad_annotation.arguments:
            return True

        if not isinstance(target, cst.Subscript):
            return False
        target_name = self._resolved_type_name(target.value)
        target_arguments = subscript_arguments(target)
        if target_name not in _OPEN_MAPPING_NAMES or target_arguments is None:
            return False
        if len(target_arguments) != len(broad_annotation.arguments):
            return False
        return self._same_syntax(target_arguments[0], broad_annotation.arguments[0])

    def _contains_broad_type(self, expression: cst.BaseExpression) -> bool:
        if self._resolved_type_name(expression) in _DIRECT_BROAD_NAMES:
            return True
        if isinstance(expression, cst.BinaryOperation) and isinstance(
            expression.operator, cst.BitOr
        ):
            return self._contains_broad_type(expression.left) or self._contains_broad_type(
                expression.right
            )
        if not isinstance(expression, cst.Subscript):
            return False
        arguments = subscript_arguments(expression)
        return arguments is not None and any(
            self._contains_broad_type(argument) for argument in arguments
        )

    def _resolved_type_name(self, expression: cst.BaseExpression) -> str | None:
        return super()._qualified_name(expression, expression)

    def _is_unconditional_scope_binding(self, node: cst.CSTNode) -> bool:
        parent = self.get_metadata(ParentNodeProvider, node, None)
        while parent is not None:
            if isinstance(parent, cst.Module | cst.FunctionDef | cst.ClassDef | cst.Lambda):
                return True
            if isinstance(
                parent,
                cst.If | cst.For | cst.While | cst.Try | cst.With | cst.Match | cst.ExceptHandler,
            ):
                return False
            parent = self.get_metadata(ParentNodeProvider, parent, None)
        return False

    @staticmethod
    def _same_syntax(left: cst.BaseExpression, right: cst.BaseExpression) -> bool:
        return cst.Module([]).code_for_node(left) == cst.Module([]).code_for_node(right)

    def _should_skip_current_file(self) -> bool:
        if self._current_file_path is None:
            return False
        return is_excluded_path(
            self._current_file_path,
            self.setting("excluded_path_parts", list[str]),
        )
