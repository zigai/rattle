from __future__ import annotations

from pathlib import Path

import libcst as cst
from libcst.metadata import (
    FilePathProvider,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle import Invalid, LintRule, RuleSetting, Valid
from rattle.rules.helpers import (
    callable_dotted_name,
    is_excluded_path,
    is_name,
    ordinary_parameters,
)


def _is_bare_object_annotation(expression: cst.BaseExpression) -> bool:
    if isinstance(expression, cst.ConcatenatedString | cst.SimpleString):
        return _is_bare_object_string_annotation(expression)

    if _is_syntactic_object_annotation(expression):
        return True

    if _is_object_none_union(expression):
        return True

    if isinstance(expression, cst.Subscript):
        return _is_bare_object_subscript_annotation(expression)

    return False


def _is_syntactic_object_annotation(expression: cst.BaseExpression) -> bool:
    return is_name(expression, "object") or callable_dotted_name(expression) == "builtins.object"


def _is_bare_object_string_annotation(
    expression: cst.ConcatenatedString | cst.SimpleString,
) -> bool:
    value = expression.evaluated_value
    if not isinstance(value, str):
        return False
    try:
        parsed_expression = cst.parse_expression(value)
    except cst.ParserSyntaxError:
        return False

    return _is_bare_object_annotation(parsed_expression)


def _is_object_none_union(expression: cst.BaseExpression) -> bool:
    if not isinstance(expression, cst.BinaryOperation) or not isinstance(
        expression.operator, cst.BitOr
    ):
        return False

    return _is_object_none_pair(expression.left, expression.right)


def _is_bare_object_subscript_annotation(expression: cst.Subscript) -> bool:
    subscript_name = callable_dotted_name(expression.value)
    elements = [
        element.slice.value for element in expression.slice if isinstance(element.slice, cst.Index)
    ]
    if subscript_name in {"Optional", "typing.Optional"} and len(elements) == 1:
        return _is_bare_object_annotation(elements[0])
    if subscript_name in {"Union", "typing.Union"} and len(elements) == 2:
        return _is_object_none_pair(elements[0], elements[1])
    if subscript_name in {
        "Annotated",
        "typing.Annotated",
        "typing_extensions.Annotated",
    }:
        return bool(elements) and _is_bare_object_annotation(elements[0])

    return False


def _is_object_none_pair(left: cst.BaseExpression, right: cst.BaseExpression) -> bool:
    return (is_name(left, "object") and is_name(right, "None")) or (
        is_name(left, "None") and is_name(right, "object")
    )


class NoBareObjectAnnotations(LintRule):
    """Require annotations to use a more precise boundary type than bare object."""

    MESSAGE = "Use a narrower type than bare object in annotations."
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
            description="Path parts that should be excluded in addition to test_*.py files.",
        ),
    }

    _current_file_path: Path | None

    VALID = [
        Valid("""
            def fn(payload: dict[str, object]) -> None:
                return None
            """),
        Valid("""
            def fn(settings_type: type[object]) -> None:
                return None
            """),
        Valid("""
            sentinel = object()
            """),
        Valid("""
            from typing import Protocol

            class SettingsProvider(Protocol):
                pass

            def fn(value: object | SettingsProvider | None) -> None:
                return None
            """),
        Valid("""
            class object:
                pass

            def fn(value: object) -> None:
                return None
            """),
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
        Invalid(
            """
            from typing import Optional

            value: Optional[object] = None
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
        Invalid(
            """
            from typing import Union

            value: Union[object, None] = None
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
        Invalid(
            """
            value: "object" = payload
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
        Invalid(
            """
            value: "object" "" = payload
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
        Invalid(
            """
            import builtins

            value: builtins.object = payload
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
        Invalid(
            """
            import builtins as builtin_types

            value: builtin_types.object = payload
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
        Invalid(
            """
            import builtins
            from typing import Optional

            value: Optional[builtins.object] = None
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
        Invalid(
            """
            from typing import Annotated

            value: Annotated[object, "metadata"] = payload
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
        Invalid(
            """
            from typing import TypeAlias

            Object: TypeAlias = object
            value: Object = payload
            """,
            expected_message="Use a narrower type than bare object in annotations.",
        ),
    ]

    def __init__(self) -> None:
        super().__init__()

        self._current_file_path = None
        self._object_type_alias_nodes: set[cst.CSTNode] = set()

    def visit_Module(self, node: cst.Module) -> None:
        file_path = self.get_metadata(FilePathProvider, node)
        self._current_file_path = file_path if isinstance(file_path, Path) else None
        self._object_type_alias_nodes = set()

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._current_file_path = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if self._should_skip_current_file():
            return

        for parameter in ordinary_parameters(node.params):
            self._report_param_if_needed(parameter)

        if node.returns is not None and self._is_bare_object_annotation(node.returns.annotation):
            self.report(node.returns, self.MESSAGE)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if self._should_skip_current_file():
            return

        self._remember_object_type_alias(node)

        if self._is_bare_object_annotation(node.annotation.annotation):
            self.report(node.annotation, self.MESSAGE)

    def _report_param_if_needed(self, parameter: cst.Param) -> None:
        if parameter.annotation is None:
            return

        if self._is_bare_object_annotation(parameter.annotation.annotation):
            self.report(parameter.annotation, self.MESSAGE)

    def _is_bare_object_annotation(self, expression: cst.BaseExpression) -> bool:
        if isinstance(expression, cst.ConcatenatedString | cst.SimpleString):
            return _is_bare_object_string_annotation(expression)

        if self._is_object_annotation_atom(expression):
            return True

        if self._is_object_none_union(expression):
            return True

        if isinstance(expression, cst.Subscript):
            return self._is_bare_object_subscript_annotation(expression)

        return False

    def _is_object_annotation_atom(self, expression: cst.BaseExpression) -> bool:
        return self._is_builtin_object_annotation(
            expression
        ) or self._is_object_type_alias_annotation(expression)

    def _is_builtin_object_annotation(self, expression: cst.BaseExpression) -> bool:
        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        if any(
            qualified_name.source is QualifiedNameSource.LOCAL for qualified_name in qualified_names
        ):
            return False
        if qualified_names:
            return any(
                qualified_name.name == "builtins.object"
                and qualified_name.source
                in {QualifiedNameSource.BUILTIN, QualifiedNameSource.IMPORT}
                for qualified_name in qualified_names
            )

        return _is_syntactic_object_annotation(expression)

    def _is_object_type_alias_annotation(self, expression: cst.BaseExpression) -> bool:
        if not isinstance(expression, cst.Name):
            return False

        scope = self.get_metadata(ScopeProvider, expression, None)
        if scope is None:
            return False

        try:
            assignments = scope[expression.value]
        except KeyError:
            return False

        return bool(assignments) and all(
            getattr(assignment, "node", None) in self._object_type_alias_nodes
            for assignment in assignments
        )

    def _is_object_none_union(self, expression: cst.BaseExpression) -> bool:
        if not isinstance(expression, cst.BinaryOperation) or not isinstance(
            expression.operator, cst.BitOr
        ):
            return False

        return self._is_object_none_pair(expression.left, expression.right)

    def _is_bare_object_subscript_annotation(self, expression: cst.Subscript) -> bool:
        elements = [
            element.slice.value
            for element in expression.slice
            if isinstance(element.slice, cst.Index)
        ]
        if (
            self._subscript_has_typing_name(
                expression,
                qualified_name="typing.Optional",
                syntactic_names={"Optional"},
            )
            and len(elements) == 1
        ):
            return self._is_bare_object_annotation(elements[0])
        if (
            self._subscript_has_typing_name(
                expression, qualified_name="typing.Union", syntactic_names={"Union"}
            )
            and len(elements) == 2
        ):
            return self._is_object_none_pair(elements[0], elements[1])
        if self._subscript_has_typing_name(
            expression, qualified_name="typing.Annotated", syntactic_names={"Annotated"}
        ) or self._subscript_has_typing_name(
            expression,
            qualified_name="typing_extensions.Annotated",
            syntactic_names={"Annotated"},
        ):
            return bool(elements) and self._is_bare_object_annotation(elements[0])

        return False

    def _subscript_has_typing_name(
        self,
        expression: cst.Subscript,
        *,
        qualified_name: str,
        syntactic_names: set[str],
    ) -> bool:
        qualified_names = self.get_metadata(QualifiedNameProvider, expression.value, set())
        if any(name.source is QualifiedNameSource.LOCAL for name in qualified_names):
            return False
        if qualified_names:
            return any(
                name.name == qualified_name and name.source is QualifiedNameSource.IMPORT
                for name in qualified_names
            )

        return callable_dotted_name(expression.value) in syntactic_names

    def _is_object_none_pair(self, left: cst.BaseExpression, right: cst.BaseExpression) -> bool:
        return (self._is_object_annotation_atom(left) and is_name(right, "None")) or (
            is_name(left, "None") and self._is_object_annotation_atom(right)
        )

    def _remember_object_type_alias(self, node: cst.AnnAssign) -> None:
        if not isinstance(node.target, cst.Name):
            return

        if (
            node.value is not None
            and self._is_type_alias_annotation(node.annotation.annotation)
            and self._is_builtin_object_annotation(node.value)
        ):
            self._object_type_alias_nodes.add(node.target)
        else:
            self._object_type_alias_nodes.discard(node.target)

    def _is_type_alias_annotation(self, expression: cst.BaseExpression) -> bool:
        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        if any(name.source is QualifiedNameSource.LOCAL for name in qualified_names):
            return False
        if qualified_names:
            return any(
                name.name in {"typing.TypeAlias", "typing_extensions.TypeAlias"}
                and name.source is QualifiedNameSource.IMPORT
                for name in qualified_names
            )

        return callable_dotted_name(expression) == "TypeAlias"

    def _should_skip_current_file(self) -> bool:
        if self._current_file_path is None:
            return False

        return is_excluded_path(self._current_file_path, self.settings["excluded_path_parts"])
