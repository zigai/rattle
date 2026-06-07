from __future__ import annotations

import libcst as cst

from rattle import Invalid, LintRule, Valid
from rattle.rules.helpers import callable_dotted_name


class NoStrExceptionTranslation(LintRule):
    """Forbid translating exceptions with str(exc) messages that discard typed context."""

    MESSAGE = (
        "Do not translate exceptions by passing str(exc); use a stable message and chain the cause."
    )

    VALID = [
        Valid(
            """
            try:
                run()
            except ValueError as exc:
                raise CommandArgumentError("Invalid resource identifier.") from exc
            """
        ),
        Valid(
            """
            message = str(value)
            """
        ),
    ]

    INVALID = [
        Invalid(
            """
            try:
                run()
            except ValueError as exc:
                raise CommandArgumentError(str(exc)) from exc
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            try:
                run()
            except ValueError as error:
                raise RuntimeError(str(error)) from error
            """,
            expected_message=MESSAGE,
        ),
    ]

    def __init__(self) -> None:
        super().__init__()

        self._exception_name_stack: list[str | None] = []

    def visit_ExceptHandler(self, node: cst.ExceptHandler) -> None:
        if isinstance(node.name, cst.AsName) and isinstance(node.name.name, cst.Name):
            self._exception_name_stack.append(node.name.name.value)
            return

        self._exception_name_stack.append(None)

    def leave_ExceptHandler(self, original_node: cst.ExceptHandler) -> None:
        del original_node
        self._exception_name_stack.pop()

    def visit_Raise(self, node: cst.Raise) -> None:
        exception_name = self._current_exception_name()
        if exception_name is None:
            return

        first_arg_value = self._first_exception_argument(node)
        if first_arg_value is None:
            return

        str_arg = self._single_str_argument(first_arg_value)
        if str_arg is None:
            return
        if str_arg.keyword is not None or not isinstance(str_arg.value, cst.Name):
            return
        if str_arg.value.value != exception_name:
            return

        self.report(first_arg_value, self.MESSAGE)

    def _current_exception_name(self) -> str | None:
        if not self._exception_name_stack:
            return None

        return self._exception_name_stack[-1]

    def _first_exception_argument(self, node: cst.Raise) -> cst.Call | None:
        if node.exc is None or not isinstance(node.exc, cst.Call):
            return None
        if not node.exc.args:
            return None

        first_arg = node.exc.args[0]
        if first_arg.keyword is not None:
            return None
        if not isinstance(first_arg.value, cst.Call):
            return None

        return first_arg.value

    def _single_str_argument(self, node: cst.Call) -> cst.Arg | None:
        if callable_dotted_name(node.func) != "str":
            return None
        if len(node.args) != 1:
            return None

        return node.args[0]
