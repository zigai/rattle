from __future__ import annotations

from pathlib import Path

import libcst as cst
from libcst.metadata import FilePathProvider

from rattle import Invalid, LintRule, RuleSetting, Valid
from rattle.rules.helpers import is_excluded_path, is_name, ordinary_parameters


def _is_bare_object_annotation(expression: cst.BaseExpression) -> bool:
    if is_name(expression, "object"):
        return True

    if not isinstance(expression, cst.BinaryOperation):
        return False
    if not isinstance(expression.operator, cst.BitOr):
        return False

    return (is_name(expression.left, "object") and is_name(expression.right, "None")) or (
        is_name(expression.left, "None") and is_name(expression.right, "object")
    )


class NoBareObjectAnnotations(LintRule):
    """Require annotations to use a more precise boundary type than bare object."""

    MESSAGE = "Use a narrower type than bare object in annotations."
    SOURCE_PATTERNS = (b"object",)
    METADATA_DEPENDENCIES = (*LintRule.METADATA_DEPENDENCIES, FilePathProvider)
    SETTINGS = {
        "excluded_path_parts": RuleSetting(
            list[str],
            default=["tests"],
            description="Path parts that should be excluded in addition to test_*.py files.",
        ),
    }

    _current_file_path: Path | None

    VALID = [
        Valid(
            """
            def fn(payload: dict[str, object]) -> None:
                return None
            """
        ),
        Valid(
            """
            def fn(settings_type: type[object]) -> None:
                return None
            """
        ),
        Valid(
            """
            sentinel = object()
            """
        ),
        Valid(
            """
            from typing import Protocol

            class SettingsProvider(Protocol):
                pass

            def fn(value: object | SettingsProvider | None) -> None:
                return None
            """
        ),
    ]

    INVALID = [
        Invalid(
            """
            def fn(value: object) -> None:
                return None
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
        Invalid(
            """
            def fn() -> object:
                return None
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
        Invalid(
            """
            value: object = payload
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
        Invalid(
            """
            value: object | None = None
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
        Invalid(
            """
            value: None | object = None
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
    ]

    def __init__(self) -> None:
        super().__init__()

        self._current_file_path = None

    def visit_Module(self, node: cst.Module) -> None:
        file_path = self.get_metadata(FilePathProvider, node)
        self._current_file_path = file_path if isinstance(file_path, Path) else None

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._current_file_path = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if self._should_skip_current_file():
            return

        for parameter in ordinary_parameters(node.params):
            self._report_param_if_needed(parameter)

        if node.returns is not None and _is_bare_object_annotation(node.returns.annotation):
            self.report(node.returns, self.MESSAGE)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if self._should_skip_current_file():
            return

        if _is_bare_object_annotation(node.annotation.annotation):
            self.report(node.annotation, self.MESSAGE)

    def _report_param_if_needed(self, parameter: cst.Param) -> None:
        if parameter.annotation is None:
            return

        if _is_bare_object_annotation(parameter.annotation.annotation):
            self.report(parameter.annotation, self.MESSAGE)

    def _should_skip_current_file(self) -> bool:
        if self._current_file_path is None:
            return False

        return is_excluded_path(self._current_file_path, self.settings["excluded_path_parts"])
