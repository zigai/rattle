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
        Valid("""
            try:
                run()
            except ValueError as exc:
                raise CommandArgumentError("Invalid resource identifier.") from exc
            """),
        Valid("""
            message = str(value)
            """),
        Valid("""
            try:
                run()
            except ValueError as exc:
                str = lambda value: "fixed"
                raise RuntimeError(str(exc)) from exc
            """),
        Valid("""
            error = "fixed"

            try:
                run()
            except ValueError as exc:
                def capture() -> None:
                    error = exc

                raise RuntimeError(str(error)) from exc
            """),
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
            try:
                run()
            except ValueError as exc:
                raise RuntimeError("%s" % (exc,)) from exc
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
        Invalid(
            """
            import builtins as builtin_values

            try:
                run()
            except ValueError as exc:
                raise RuntimeError(builtin_values.str(exc)) from exc
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            from builtins import str as stringify

            try:
                run()
            except ValueError as exc:
                raise RuntimeError(stringify(exc)) from exc
            """,
            expected_message=MESSAGE,
        ),
    ]

    def __init__(self) -> None:
        super().__init__()

        self._exception_name_stack: list[tuple[set[str], int]] = []
        self._scope_depth = 0

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        del node
        self._scope_depth += 1

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        del original_node
        self._scope_depth -= 1

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        del node
        self._scope_depth += 1

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        del original_node
        self._scope_depth -= 1

    def visit_ExceptHandler(self, node: cst.ExceptHandler) -> None:
        if isinstance(node.name, cst.AsName) and isinstance(node.name.name, cst.Name):
            self._exception_name_stack.append(({node.name.name.value}, self._scope_depth))
            return

        self._exception_name_stack.append((set(), self._scope_depth))

    def leave_ExceptHandler(self, original_node: cst.ExceptHandler) -> None:
        del original_node
        self._exception_name_stack.pop()

    def visit_Assign(self, node: cst.Assign) -> None:
        if not self._exception_name_stack:
            return

        current_exception_names = self._current_exception_names()
        for target in node.targets:
            if not isinstance(target.target, cst.Name):
                continue
            if self._is_exception_name(node.value, current_exception_names):
                current_exception_names.add(target.target.value)
            else:
                current_exception_names.discard(target.target.value)

    def visit_Raise(self, node: cst.Raise) -> None:
        exception_names = self._current_exception_names()
        if not exception_names:
            return

        for argument in self._exception_arguments(node):
            if self._translates_exception(argument.value, exception_names):
                self.report(argument.value, self.MESSAGE)
                return

    def _current_exception_names(self) -> set[str]:
        if not self._exception_name_stack:
            return set()

        exception_names, scope_depth = self._exception_name_stack[-1]
        if scope_depth != self._scope_depth:
            return set()

        return exception_names

    def _exception_arguments(self, node: cst.Raise) -> tuple[cst.Arg, ...]:
        if node.exc is None or not isinstance(node.exc, cst.Call):
            return ()

        return tuple(node.exc.args)

    def _translates_exception(self, node: cst.BaseExpression, exception_names: set[str]) -> bool:
        if isinstance(node, cst.Call):
            str_arg = self._single_builtin_str_argument(node)
            if str_arg is not None:
                return self._is_exception_name(str_arg.value, exception_names)

            format_arg = self._single_format_argument(node)
            if format_arg is not None:
                return self._is_exception_name(format_arg.value, exception_names)

        if isinstance(node, cst.FormattedString):
            return self._is_exception_only_f_string(node, exception_names)

        if isinstance(node, cst.BinaryOperation) and isinstance(node.operator, cst.Modulo):
            return self._is_exception_name_or_singleton_tuple(node.right, exception_names)

        return False

    def _single_builtin_str_argument(self, node: cst.Call) -> cst.Arg | None:
        if len(node.args) != 1:
            return None

        if not self._is_builtin_str(node.func):
            return None

        return node.args[0]

    def _is_builtin_str(self, node: cst.BaseExpression) -> bool:
        return QualifiedNameProvider.has_name(
            self,
            node,
            QualifiedName(name="builtins.str", source=QualifiedNameSource.BUILTIN),
        ) or QualifiedNameProvider.has_name(
            self,
            node,
            QualifiedName(name="builtins.str", source=QualifiedNameSource.IMPORT),
        )

    def _single_format_argument(self, node: cst.Call) -> cst.Arg | None:
        if callable_dotted_name(node.func) != "format":
            return None
        if len(node.args) != 1:
            return None

        return node.args[0]

    def _is_exception_only_f_string(
        self,
        node: cst.FormattedString,
        exception_names: set[str],
    ) -> bool:
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

        return self._is_exception_name(expressions[0].expression, exception_names)

    def _is_exception_name(self, node: cst.BaseExpression, exception_names: set[str]) -> bool:
        return isinstance(node, cst.Name) and node.value in exception_names

    def _is_exception_name_or_singleton_tuple(
        self,
        node: cst.BaseExpression,
        exception_names: set[str],
    ) -> bool:
        if self._is_exception_name(node, exception_names):
            return True
        if not isinstance(node, cst.Tuple) or len(node.elements) != 1:
            return False

        return self._is_exception_name(node.elements[0].value, exception_names)
