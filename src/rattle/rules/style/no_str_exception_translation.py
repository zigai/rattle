from __future__ import annotations

import libcst as cst
from libcst.metadata import QualifiedName, QualifiedNameProvider, QualifiedNameSource

from rattle import Invalid, LintRule, Valid
from rattle.rules.helpers import callable_dotted_name


class NoStrExceptionTranslation(LintRule):
    """Forbid translating exceptions with str(exc) messages that discard typed context."""

    MESSAGE = (
        "Do not translate exceptions by passing str(exc); use a stable message and chain the cause."
    )
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)

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
        Valid(
            """
            try:
                run()
            except ValueError as exc:
                str = lambda value: "fixed"
                raise RuntimeError(str(exc)) from exc
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
        Invalid(
            """
            try:
                run()
            except ValueError as exc:
                raise RuntimeError(message=str(exc)) from exc
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            try:
                run()
            except ValueError as exc:
                raise RuntimeError(f"{exc}") from exc
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            try:
                run()
            except ValueError as exc:
                raise RuntimeError("{}".format(exc)) from exc
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            try:
                run()
            except ValueError as exc:
                raise RuntimeError("%s" % exc) from exc
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            import builtins

            try:
                run()
            except ValueError as exc:
                raise RuntimeError(builtins.str(exc)) from exc
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

        for argument in self._exception_arguments(node):
            if self._translates_exception(argument.value, exception_name):
                self.report(argument.value, self.MESSAGE)
                return

    def _current_exception_name(self) -> str | None:
        if not self._exception_name_stack:
            return None

        return self._exception_name_stack[-1]

    def _exception_arguments(self, node: cst.Raise) -> tuple[cst.Arg, ...]:
        if node.exc is None or not isinstance(node.exc, cst.Call):
            return ()

        return tuple(node.exc.args)

    def _translates_exception(self, node: cst.BaseExpression, exception_name: str) -> bool:
        if isinstance(node, cst.Call):
            str_arg = self._single_builtin_str_argument(node)
            if str_arg is not None:
                return self._is_exception_name(str_arg.value, exception_name)

            format_arg = self._single_format_argument(node)
            if format_arg is not None:
                return self._is_exception_name(format_arg.value, exception_name)

        if isinstance(node, cst.FormattedString):
            return self._is_exception_only_f_string(node, exception_name)

        if isinstance(node, cst.BinaryOperation) and isinstance(node.operator, cst.Modulo):
            return self._is_exception_name(node.right, exception_name)

        return False

    def _single_builtin_str_argument(self, node: cst.Call) -> cst.Arg | None:
        if callable_dotted_name(node.func) not in {"str", "builtins.str"}:
            return None
        if len(node.args) != 1:
            return None

        if (
            not QualifiedNameProvider.has_name(
                self,
                node.func,
                QualifiedName(name="builtins.str", source=QualifiedNameSource.BUILTIN),
            )
            and callable_dotted_name(node.func) != "builtins.str"
        ):
            return None

        return node.args[0]

    def _single_format_argument(self, node: cst.Call) -> cst.Arg | None:
        if callable_dotted_name(node.func) != "format":
            return None
        if len(node.args) != 1:
            return None

        return node.args[0]

    def _is_exception_only_f_string(self, node: cst.FormattedString, exception_name: str) -> bool:
        expressions = [
            part for part in node.parts if isinstance(part, cst.FormattedStringExpression)
        ]
        text_parts = [
            part.value
            for part in node.parts
            if isinstance(part, cst.FormattedStringText) and part.value
        ]
        if text_parts or len(expressions) != 1:
            return False

        return self._is_exception_name(expressions[0].expression, exception_name)

    def _is_exception_name(self, node: cst.BaseExpression, exception_name: str) -> bool:
        return isinstance(node, cst.Name) and node.value == exception_name
