from __future__ import annotations

from collections.abc import Sequence

import libcst as cst

from rattle import Invalid, LintRule, Valid
from rattle.rules.helpers import is_name, ordinary_parameters, single_small_statement


def _is_all_assignment(statement: cst.BaseSmallStatement) -> bool:
    if isinstance(statement, cst.Assign):
        return any(is_name(target.target, "__all__") for target in statement.targets)

    if not isinstance(statement, cst.AnnAssign):
        return False

    return is_name(statement.target, "__all__")


def _is_all_mutation(statement: cst.BaseSmallStatement) -> bool:
    if isinstance(statement, cst.AugAssign):
        return isinstance(statement.operator, cst.AddAssign) and is_name(
            statement.target, "__all__"
        )

    if not isinstance(statement, cst.Expr):
        return False
    if not isinstance(statement.value, cst.Call):
        return False
    if not isinstance(statement.value.func, cst.Attribute):
        return False
    if not is_name(statement.value.func.value, "__all__"):
        return False

    return statement.value.func.attr.value in {"append", "extend", "insert"}


def _is_all_statement(statement: cst.BaseSmallStatement) -> bool:
    return _is_all_assignment(statement) or _is_all_mutation(statement)


def _module_uses_future_annotations(node: cst.Module) -> bool:
    for statement in node.body:
        import_from = single_small_statement(statement)
        if not isinstance(import_from, cst.ImportFrom):
            continue
        if not is_name(import_from.module, "__future__"):
            continue
        if isinstance(import_from.names, cst.ImportStar):
            continue

        for alias in import_from.names:
            if is_name(alias.name, "annotations"):
                return True

    return False


def _parameter_annotation_is_safe(
    parameter: cst.Param,
    *,
    future_annotations_enabled: bool,
) -> bool:
    return future_annotations_enabled or parameter.annotation is None


def _parameters_are_safe(
    parameters: cst.Parameters,
    *,
    future_annotations_enabled: bool,
) -> bool:
    for parameter in ordinary_parameters(parameters):
        if parameter.default is not None:
            return False
        if not _parameter_annotation_is_safe(
            parameter,
            future_annotations_enabled=future_annotations_enabled,
        ):
            return False

    return True


def _is_safe_function_definition(
    statement: cst.BaseStatement,
    *,
    future_annotations_enabled: bool,
) -> bool:
    if not isinstance(statement, cst.FunctionDef):
        return False
    if statement.decorators:
        return False
    if statement.type_parameters is not None:
        return False
    if not future_annotations_enabled and statement.returns is not None:
        return False

    return _parameters_are_safe(
        statement.params,
        future_annotations_enabled=future_annotations_enabled,
    )


def _all_assignment_indices(node: cst.Module) -> list[int]:
    indices: list[int] = []
    for index, statement in enumerate(node.body):
        small_statement = single_small_statement(statement)
        if small_statement is None:
            continue

        if not _is_all_assignment(small_statement):
            continue
        indices.append(index)

    return indices


def _movable_all_assignment_statement(
    node: cst.Module, all_assignment_index: int
) -> cst.SimpleStatementLine | None:
    all_assignment_statement = node.body[all_assignment_index]
    if not isinstance(all_assignment_statement, cst.SimpleStatementLine):
        return None
    if any(line.comment is not None for line in all_assignment_statement.leading_lines):
        return None

    return all_assignment_statement


def _safe_trailing_statements(
    trailing_statements: tuple[cst.BaseStatement, ...],
    *,
    future_annotations_enabled: bool,
    strip_first_leading_lines: bool,
) -> list[cst.BaseStatement] | None:
    if not trailing_statements:
        return None
    if not all(
        _is_safe_function_definition(
            statement,
            future_annotations_enabled=future_annotations_enabled,
        )
        for statement in trailing_statements
    ):
        return None

    reordered_trailing_statements: list[cst.BaseStatement] = list(trailing_statements)
    if not strip_first_leading_lines:
        return reordered_trailing_statements

    first_trailing_statement = reordered_trailing_statements[0]
    if not isinstance(first_trailing_statement, cst.FunctionDef):
        return None
    if any(line.comment is not None for line in first_trailing_statement.leading_lines):
        return None

    reordered_trailing_statements[0] = first_trailing_statement.with_changes(leading_lines=[])

    return reordered_trailing_statements


def _build_safe_replacement(node: cst.Module) -> cst.Module | None:
    future_annotations_enabled = _module_uses_future_annotations(node)
    all_assignment_indices = _all_assignment_indices(node)

    if len(all_assignment_indices) != 1:
        return None

    all_assignment_index = all_assignment_indices[0]
    if all_assignment_index == len(node.body) - 1:
        return None

    all_assignment_statement = _movable_all_assignment_statement(node, all_assignment_index)
    if all_assignment_statement is None:
        return None

    reordered_trailing_statements = _safe_trailing_statements(
        tuple(node.body[all_assignment_index + 1 :]),
        future_annotations_enabled=future_annotations_enabled,
        strip_first_leading_lines=all_assignment_index == 0,
    )
    if reordered_trailing_statements is None:
        return None

    moved_statement = all_assignment_statement.with_changes(leading_lines=[cst.EmptyLine()])
    reordered_body = [
        *node.body[:all_assignment_index],
        *reordered_trailing_statements,
        moved_statement,
    ]
    return node.with_changes(body=reordered_body)


class ModuleStatementCollector(cst.CSTVisitor):
    def __init__(self) -> None:
        self.entries: list[tuple[cst.CSTNode, bool]] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self.entries.append((node, False))
        return False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        self.entries.append((node, False))
        return False

    def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> bool:
        self._remember_small_statements(node.body)
        return False

    def visit_SimpleStatementSuite(self, node: cst.SimpleStatementSuite) -> bool:
        self._remember_small_statements(node.body)
        return False

    def _remember_small_statements(
        self,
        statements: Sequence[cst.BaseSmallStatement],
    ) -> None:
        self.entries.extend((statement, _is_all_statement(statement)) for statement in statements)


class ModuleAllAtBottom(LintRule):
    """Require module __all__ declarations to appear after runtime definitions."""

    MESSAGE = "Define module __all__ at the bottom of the file."

    VALID = [
        Valid(
            """
            from package import value

            def build() -> str:
                return value

            __all__ = ["build"]
            """
        ),
        Valid(
            '''
            """Module docstring."""

            class Exported:
                pass

            __all__: list[str] = ["Exported"]
            '''
        ),
    ]

    INVALID = [
        Invalid(
            """
            __all__ = ["build"]

            def build():
                return "value"
            """,
            expected_replacement="""
            def build():
                return "value"

            __all__ = ["build"]
            """,
        ),
        Invalid(
            """
            __all__: list[str] = ["Exported"]

            class Exported:
                pass
            """
        ),
        Invalid(
            """
            from package import value

            __all__ = ["value"]
            value = "updated"
            """
        ),
        Invalid(
            """
            __all__ = []
            __all__.append("build")

            def build():
                return "value"
            """
        ),
        Invalid(
            """
            __all__ += ["build"]

            def build():
                return "value"
            """
        ),
        Invalid(
            """
            __all__.insert(0, "build")

            def build():
                return "value"
            """
        ),
    ]

    def visit_Module(self, node: cst.Module) -> None:
        replacement = _build_safe_replacement(node)
        if replacement is not None:
            self.report(node, self.MESSAGE, replacement=replacement)
            return

        collector = ModuleStatementCollector()
        node.visit(collector)
        last_non_all_index = max(
            (
                index
                for index, (_statement, is_all_statement) in enumerate(collector.entries)
                if not is_all_statement
            ),
            default=-1,
        )
        for index, (statement, is_all_statement) in enumerate(collector.entries):
            if is_all_statement and index < last_non_all_index:
                self.report(statement, self.MESSAGE)
