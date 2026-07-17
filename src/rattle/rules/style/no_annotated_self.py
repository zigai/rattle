from __future__ import annotations

import libcst as cst
from libcst.metadata import (
    ParentNodeProvider,
    QualifiedName,
    QualifiedNameProvider,
    QualifiedNameSource,
)

from rattle import Invalid, LintRule, Valid


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
        if not self._is_direct_class_member(node):
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

        self.report(
            parameter,
            self.MESSAGE,
            replacement=parameter.with_changes(annotation=None),
        )

    def _is_direct_class_member(self, node: cst.FunctionDef) -> bool:
        parent = self.get_metadata(ParentNodeProvider, node, None)
        while parent is not None:
            if isinstance(parent, cst.ClassDef):
                return True
            if isinstance(parent, cst.FunctionDef | cst.Lambda):
                return False
            parent = self.get_metadata(ParentNodeProvider, parent, None)
        return False

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
