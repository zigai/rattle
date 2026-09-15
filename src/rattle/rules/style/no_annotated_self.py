from __future__ import annotations

import libcst as cst
import libcst.matchers as m
from libcst.metadata import (
    ParentNodeProvider,
    QualifiedName,
    QualifiedNameProvider,
    QualifiedNameSource,
)

from rattle.rule import Invalid, LintRule, Valid
from rattle.rules.helpers import is_in_class_scope


def _first_parameter(parameters: cst.Parameters) -> cst.Param | None:
    if parameters.posonly_params:
        return parameters.posonly_params[0]
    if parameters.params:
        return parameters.params[0]

    return None


class NoAnnotatedSelf(LintRule):
    """Forbid explicit type annotations on instance-method self parameters."""

    MESSAGE = "Do not annotate self in instance methods."
    METADATA_DEPENDENCIES = (ParentNodeProvider, QualifiedNameProvider)

    VALID = [
        Valid(
            """
            class A:
                def method(self, value: int) -> int:
                    return value
            """
        ),
        Valid(
            """
            def helper(self: object, value: int) -> int:
                return value
            """
        ),
        Valid(
            """
            class A:
                @classmethod
                def build(cls, value: int) -> "A":
                    return cls()
            """
        ),
        Valid(
            """
            class A:
                @classmethod
                def build(self: type["A"]) -> "A":
                    return self()
            """
        ),
        Valid(
            """
            from builtins import classmethod as cm

            class A:
                @cm
                def build(self: type["A"]) -> "A":
                    return self()
            """
        ),
        Valid(
            """
            class A:
                @staticmethod
                def helper(self: int) -> None:
                    pass
            """
        ),
        Valid(
            """
            from builtins import staticmethod as sm

            class A:
                @sm
                def helper(self: int) -> None:
                    pass
            """
        ),
        Valid(
            """
            import builtins as builtin_values

            class A:
                @builtin_values.staticmethod
                def helper(self: int) -> None:
                    pass
            """
        ),
        Valid(
            """
            from typing import TypeVar

            T = TypeVar("T", bound="Query")

            class Query:
                def filter(self: T, condition: str) -> T:
                    return self
            """
        ),
    ]

    INVALID = [
        Invalid(
            """
            class A:
                def method(self: "A", value: int) -> int:
                    return value
            """,
            expected_replacement="""
            class A:
                def method(self, value: int) -> int:
                    return value
            """,
        ),
        Invalid(
            """
            class A:
                async def method(self: "A") -> None:
                    return None
            """,
            expected_replacement="""
            class A:
                async def method(self) -> None:
                    return None
            """,
        ),
        Invalid(
            """
            def outer():
                class A:
                    def method(self: "A") -> None:
                        pass
            """,
            expected_replacement="""
            def outer():
                class A:
                    def method(self) -> None:
                        pass
            """,
        ),
    ]

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if not is_in_class_scope(self, node):
            return
        if self._is_non_instance_method(node):
            return

        parameter = _first_parameter(node.params)
        if parameter is None:
            return
        if parameter.name.value != "self":
            return
        if parameter.annotation is None:
            return
        if not self._should_report_self_annotation(node, parameter):
            return

        self.report(
            parameter,
            self.MESSAGE,
            replacement=parameter.with_changes(annotation=None),
        )

    def _enclosing_class_name(self, node: cst.FunctionDef) -> str | None:
        parent: cst.CSTNode | None = self.get_metadata(ParentNodeProvider, node, None)
        while parent and not isinstance(parent, cst.ClassDef):
            parent = self.get_metadata(ParentNodeProvider, parent, None)
        return parent.name.value if isinstance(parent, cst.ClassDef) else None

    def _should_report_self_annotation(self, node: cst.FunctionDef, parameter: cst.Param) -> bool:
        if parameter.annotation is None:
            return False
        if node.name.value == "__new__":
            return False

        annot_expr = parameter.annotation.annotation
        if isinstance(annot_expr, cst.Subscript):
            return False

        annot_names = self._extract_annotation_names(annot_expr)
        class_name = self._enclosing_class_name(node)

        if class_name and (class_name in annot_names or "Self" in annot_names):
            return True

        if node.returns is not None:
            return_names = self._extract_annotation_names(node.returns.annotation)
            if annot_names & return_names:
                return False

        return True

    @staticmethod
    def _extract_annotation_names(annot_expr: cst.BaseExpression) -> set[str]:
        if isinstance(annot_expr, cst.SimpleString):
            return {annot_expr.value.strip("'\"")}
        return {n.value for n in m.findall(annot_expr, m.Name()) if isinstance(n, cst.Name)}

    def _is_non_instance_method(self, node: cst.FunctionDef) -> bool:
        return any(
            self._is_builtin_method_decorator(decorator.decorator) for decorator in node.decorators
        )

    def _is_builtin_method_decorator(self, node: cst.BaseExpression) -> bool:
        return any(
            QualifiedNameProvider.has_name(
                self,
                node,
                QualifiedName(name=name, source=source),
            )
            for name in ("builtins.classmethod", "builtins.staticmethod")
            for source in (QualifiedNameSource.BUILTIN, QualifiedNameSource.IMPORT)
        )
