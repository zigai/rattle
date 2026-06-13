from __future__ import annotations

import libcst as cst

from rattle import Invalid, LintRule, Valid
from rattle.rules.helpers import callable_dotted_name, is_name, single_small_statement

SuiteNode = cst.Module | cst.IndentedBlock


class NameUseCounter(cst.CSTVisitor):
    def __init__(self, name: str) -> None:
        self.name = name
        self.count = 0

    def visit_Name(self, node: cst.Name) -> None:
        if node.value == self.name:
            self.count += 1

    def visit_Arg(self, node: cst.Arg) -> bool:
        node.value.visit(self)
        return False


def _name_use_count(node: cst.CSTNode, name: str) -> int:
    counter = NameUseCounter(name)
    node.visit(counter)
    return counter.count


def _message_assignment(statement: cst.BaseStatement) -> tuple[str, cst.BaseExpression] | None:
    small_statement = single_small_statement(statement, allow_leading_lines=False)
    if isinstance(small_statement, cst.Assign):
        if len(small_statement.targets) != 1:
            return None
        target = small_statement.targets[0].target
        value = small_statement.value
    elif isinstance(small_statement, cst.AnnAssign):
        target = small_statement.target
        value = small_statement.value
        if value is None:
            return None
    else:
        return None
    if not isinstance(target, cst.Name):
        return None
    if _looks_like_exception_object(value):
        return None

    return target.value, value


def _raise_statement(statement: cst.BaseStatement) -> cst.Raise | None:
    small_statement = single_small_statement(statement)
    if isinstance(small_statement, cst.Raise):
        return small_statement

    return None


def _looks_like_exception_object(value: cst.BaseExpression) -> bool:
    if not isinstance(value, cst.Call):
        return False

    name = callable_dotted_name(value.func)
    if name is None:
        return False

    class_name = name.rsplit(".", 1)[-1]
    return class_name.endswith(("Error", "Exception"))


def _inline_exception_argument(
    raise_statement: cst.Raise,
    *,
    variable_name: str,
    value: cst.BaseExpression,
) -> cst.Raise | None:
    if _name_use_count(raise_statement, variable_name) != 1:
        return None

    exception = raise_statement.exc
    if not isinstance(exception, cst.Call):
        return None

    replaced_count = 0
    arguments: list[cst.Arg] = []
    for argument in exception.args:
        if is_name(argument.value, variable_name):
            arguments.append(argument.with_changes(value=value))
            replaced_count += 1
            continue

        arguments.append(argument)

    if replaced_count != 1:
        return None

    return raise_statement.with_changes(exc=exception.with_changes(args=arguments))


def _updated_raise_line(
    statement: cst.BaseStatement,
    *,
    variable_name: str,
    value: cst.BaseExpression,
) -> cst.BaseStatement | None:
    raise_statement = _raise_statement(statement)
    if raise_statement is None:
        return None

    replacement = _inline_exception_argument(
        raise_statement,
        variable_name=variable_name,
        value=value,
    )
    if replacement is None:
        return None

    return statement.with_changes(body=[replacement])


def _suite_replacement(suite: SuiteNode) -> SuiteNode | None:
    body = suite.body
    for index, statement in enumerate(body[:-1]):
        assignment = _message_assignment(statement)
        if assignment is None:
            continue

        variable_name, value = assignment
        updated_raise = _updated_raise_line(
            body[index + 1],
            variable_name=variable_name,
            value=value,
        )
        if updated_raise is None:
            continue

        return suite.with_changes(body=(*body[:index], updated_raise, *body[index + 2 :]))

    return None


class NoExceptionMessageVariables(LintRule):
    """Forbid throwaway local variables used only as exception messages."""

    MESSAGE = "Inline exception message strings instead of assigning throwaway variables."

    VALID = [
        Valid(
            """
            msg = "invalid value"
            logger.warning(msg)
            raise ValueError(msg)
            """
        ),
        Valid(
            """
            msg = "invalid value"
            raise ValueError(f"{msg}: {value}")
            """
        ),
        Valid(
            """
            raise ValueError("invalid value")
            """
        ),
        Valid(
            """
            err = PermissionError("invalid value")
            raise RuntimeError(err)
            """
        ),
        Valid(
            """
            msg = "invalid value"
            raise ValueError(msg) from msg
            """
        ),
    ]

    INVALID = [
        Invalid(
            """
            message = build_message()
            raise ValueError(message)
            """,
            expected_replacement="""
            raise ValueError(build_message())
            """,
        ),
        Invalid(
            """
            msg = "invalid value"
            raise ValueError(msg)
            """,
            expected_replacement="""
            raise ValueError("invalid value")
            """,
        ),
        Invalid(
            """
            msg: str = "invalid value"
            raise ValueError(msg)
            """,
            expected_replacement="""
            raise ValueError("invalid value")
            """,
        ),
        Invalid(
            """
            msg = "invalid value"
            # keep this comment attached to the raise
            raise ValueError(msg)
            """,
            expected_replacement="""
            # keep this comment attached to the raise
            raise ValueError("invalid value")
            """,
        ),
        Invalid(
            """
            message = f"invalid value: {value}"
            raise RuntimeError(message) from exc
            """,
            expected_replacement="""
            raise RuntimeError(f"invalid value: {value}") from exc
            """,
        ),
        Invalid(
            """
            detail = "invalid value"
            raise CustomError(code=code, detail=detail)
            """,
            expected_replacement="""
            raise CustomError(code=code, detail="invalid value")
            """,
        ),
    ]

    def visit_Module(self, node: cst.Module) -> None:
        self._report_suite(node)

    def visit_IndentedBlock(self, node: cst.IndentedBlock) -> None:
        self._report_suite(node)

    def _report_suite(self, node: SuiteNode) -> None:
        replacement = _suite_replacement(node)
        if replacement is None:
            return

        self.report(node, self.MESSAGE, replacement=replacement)
