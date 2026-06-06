from __future__ import annotations

import libcst as cst

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
    ]

    def __init__(self) -> None:
        super().__init__()

        self._class_depth = 0
        self._function_depth = 0

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        del node

        self._class_depth += 1

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        del original_node

        self._class_depth -= 1

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        is_direct_class_method = self._class_depth > 0 and self._function_depth == 0
        self._function_depth += 1

        if not is_direct_class_method:
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

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        del original_node

        self._function_depth -= 1
