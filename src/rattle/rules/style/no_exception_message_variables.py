from __future__ import annotations

import libcst as cst
from libcst.metadata import PositionProvider, ScopeProvider
from libcst.metadata.scope_provider import Assignment

from rattle import Invalid, LintRule, Valid
from rattle.rules.helpers import callable_dotted_name, single_small_statement

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


def _message_assignment(statement: cst.BaseStatement) -> tuple[cst.Name, cst.BaseExpression] | None:
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

    return target, value


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
) -> tuple[cst.Raise, cst.Name] | None:
    if _name_use_count(raise_statement, variable_name) != 1:
        return None

    exception = raise_statement.exc
    if not isinstance(exception, cst.Call):
        return None

    replaced_count = 0
    replaced_name: cst.Name | None = None
    arguments: list[cst.Arg] = []
    for argument in exception.args:
        if isinstance(argument.value, cst.Name) and argument.value.value == variable_name:
            arguments.append(argument.with_changes(value=value))
            replaced_count += 1
            replaced_name = argument.value
            continue

        arguments.append(argument)

    if replaced_count != 1 or replaced_name is None:
        return None

    return (
        raise_statement.with_changes(exc=exception.with_changes(args=arguments)),
        replaced_name,
    )


def _updated_raise_line(
    statement: cst.BaseStatement,
    *,
    variable_name: str,
    value: cst.BaseExpression,
) -> tuple[cst.BaseStatement, cst.Name] | None:
    raise_statement = _raise_statement(statement)
    if raise_statement is None:
        return None

    replacement_and_name = _inline_exception_argument(
        raise_statement,
        variable_name=variable_name,
        value=value,
    )
    if replacement_and_name is None:
        return None
    replacement, replaced_name = replacement_and_name

    return statement.with_changes(body=[replacement]), replaced_name


def _suite_replacement(
    suite: SuiteNode,
) -> tuple[SuiteNode, cst.Name, cst.Name] | None:
    body = suite.body
    for index, statement in enumerate(body[:-1]):
        assignment = _message_assignment(statement)
        if assignment is None:
            continue

        target, value = assignment
        updated_raise_and_name = _updated_raise_line(
            body[index + 1],
            variable_name=target.value,
            value=value,
        )
        if updated_raise_and_name is None:
            continue
        updated_raise, replaced_name = updated_raise_and_name

        replacement = suite.with_changes(body=(*body[:index], updated_raise, *body[index + 2 :]))
        return replacement, target, replaced_name

    return None


class NoExceptionMessageVariables(LintRule):
    """Forbid throwaway local variables used only as exception messages."""

    MESSAGE = "Inline exception message strings instead of assigning throwaway variables."
    METADATA_DEPENDENCIES = (PositionProvider, ScopeProvider)

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
        replacement_and_names = _suite_replacement(node)
        if replacement_and_names is None:
            return
        replacement, target, reference = replacement_and_names
        if not self._is_only_reference(target, reference):
            return

        self.report(node, self.MESSAGE, replacement=replacement)

    def _is_only_reference(self, target: cst.Name, reference: cst.Name) -> bool:
        scope = self.get_metadata(ScopeProvider, target, None)
        if scope is None:
            return False

        try:
            assignments = scope[target.value]
        except KeyError:
            return False

        concrete_assignments = [
            assignment for assignment in assignments if isinstance(assignment, Assignment)
        ]
        matching_assignments = [
            assignment for assignment in concrete_assignments if assignment.node is target
        ]
        if len(matching_assignments) != 1:
            return False

        target_position = self._position(target)
        if target_position is None:
            return False

        next_assignment_position = self._next_assignment_position(
            concrete_assignments,
            target,
            target_position,
        )
        relevant_references = self._relevant_references(
            concrete_assignments,
            target_position,
            next_assignment_position,
        )
        return relevant_references == {reference}

    def _next_assignment_position(
        self,
        assignments: list[Assignment],
        target: cst.Name,
        target_position: tuple[int, int],
    ) -> tuple[int, int] | None:
        positions = [
            position
            for assignment in assignments
            if assignment.node is not target
            if (position := self._position(assignment.node)) is not None
            if position > target_position
        ]
        return min(positions, default=None)

    def _relevant_references(
        self,
        assignments: list[Assignment],
        target_position: tuple[int, int],
        next_assignment_position: tuple[int, int] | None,
    ) -> set[cst.CSTNode]:
        references: set[cst.CSTNode] = set()
        for assignment in assignments:
            for access in assignment.references:
                position = self._position(access.node)
                if position is None or position <= target_position:
                    continue
                if next_assignment_position is not None and position >= next_assignment_position:
                    continue
                references.add(access.node)

        return references

    def _position(self, node: cst.CSTNode) -> tuple[int, int] | None:
        code_range = self.get_metadata(PositionProvider, node, None)
        if code_range is None:
            return None

        return code_range.start.line, code_range.start.column
