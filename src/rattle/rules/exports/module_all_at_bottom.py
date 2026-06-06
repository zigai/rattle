from __future__ import annotations

import libcst as cst

from rattle import Invalid, LintRule, Valid


def _is_all_assignment(statement: cst.BaseSmallStatement) -> bool:
    if isinstance(statement, cst.Assign):
        return any(
            isinstance(target.target, cst.Name) and target.target.value == "__all__"
            for target in statement.targets
        )

    if not isinstance(statement, cst.AnnAssign):
        return False

    return isinstance(statement.target, cst.Name) and statement.target.value == "__all__"


def _module_uses_future_annotations(node: cst.Module) -> bool:
    for statement in node.body:
        if not isinstance(statement, cst.SimpleStatementLine):
            continue
        if len(statement.body) != 1:
            continue

        import_from = statement.body[0]
        if not isinstance(import_from, cst.ImportFrom):
            continue
        if not isinstance(import_from.module, cst.Name) or import_from.module.value != "__future__":
            continue
        if isinstance(import_from.names, cst.ImportStar):
            continue

        for alias in import_from.names:
            if isinstance(alias.name, cst.Name) and alias.name.value == "annotations":
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
    ordinary_parameters: list[cst.Param] = [
        *parameters.posonly_params,
        *parameters.params,
        *parameters.kwonly_params,
    ]

    if isinstance(parameters.star_arg, cst.Param):
        ordinary_parameters.append(parameters.star_arg)

    if parameters.star_kwarg is not None:
        ordinary_parameters.append(parameters.star_kwarg)

    for parameter in ordinary_parameters:
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
        if not isinstance(statement, cst.SimpleStatementLine):
            continue

        if len(statement.body) != 1:
            continue

        if not _is_all_assignment(statement.body[0]):
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


class ModuleAllAtBottom(LintRule):
    """Require module __all__ declarations to appear after runtime definitions."""

    MESSAGE = "Define module __all__ at the bottom of the file."
    TAGS = {"exports", "style"}

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
    ]

    def visit_Module(self, node: cst.Module) -> None:
        replacement = _build_safe_replacement(node)
        if replacement is not None:
            self.report(node, self.MESSAGE, replacement=replacement)
            return

        last_statement_index = len(node.body) - 1
        for statement_index, statement in enumerate(node.body):
            if not isinstance(statement, cst.SimpleStatementLine):
                continue

            last_small_statement_index = len(statement.body) - 1
            for small_statement_index, small_statement in enumerate(statement.body):
                if not _is_all_assignment(small_statement):
                    continue
                if (
                    statement_index == last_statement_index
                    and small_statement_index == last_small_statement_index
                ):
                    continue

                self.report(small_statement, self.MESSAGE)
