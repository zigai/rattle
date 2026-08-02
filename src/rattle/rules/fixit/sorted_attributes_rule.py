# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
import libcst.matchers as m

from rattle import Invalid, LintRule, Valid
from rattle.rules.helpers import is_static_literal_expression

LineType = cst.BaseSmallStatement | cst.BaseStatement


class SortedAttributes(LintRule):
    """
    Sort contiguous class assignment groups when the class docstring contains
    ``@sorted-attributes``. Reordering assignments can change the order in which
    right-hand-side expressions run, so use this directive only for side-effect-free
    class attributes.
    """

    INVALID = [
        Invalid(
            """
            class MyUnsortedConstants:
                \"\"\"
                @sorted-attributes
                \"\"\"
                z = "hehehe"
                B = 'aaa234'
                A = 'zzz123'
                cab = "foo bar"
                Daaa = "banana"

                @classmethod
                def get_foo(cls) -> str:
                    return "some random thing"
           """,
            expected_replacement="""
            class MyUnsortedConstants:
                \"\"\"
                @sorted-attributes
                \"\"\"
                A = 'zzz123'
                B = 'aaa234'
                Daaa = "banana"
                cab = "foo bar"
                z = "hehehe"

                @classmethod
                def get_foo(cls) -> str:
                    return "some random thing"
           """,
        ),
        Invalid(
            """
            class MyUnsortedConstants:
                \"\"\"
                @sorted-attributes
                \"\"\"
                z: int = 1
                a: int = 2
           """,
            expected_replacement="""
            class MyUnsortedConstants:
                \"\"\"
                @sorted-attributes
                \"\"\"
                a: int = 2
                z: int = 1
           """,
        ),
    ]
    MESSAGE: str = (
        "Class assignments under @sorted-attributes are not sorted; sorting them can "
        "change right-hand-side side-effect order."
    )
    VALID = [
        Valid(
            """
            class MyConstants:
                \"\"\"
                @sorted-attributes
                \"\"\"
                A = 'zzz123'
                B = 'aaa234'

            class MyUnsortedConstants:
                B = 'aaa234'
                A = 'zzz123'
           """
        ),
        Valid(
            """
            class MyConstants:
                \"\"\"
                @sorted-attributes
                \"\"\"
                z = side_effect("z")

                def method(self):
                    pass

                a = side_effect("a")
            """
        ),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._fixed_classes: dict[cst.ClassDef, cst.ClassDef] = {}

    def visit_Module(self, node: cst.Module) -> None:
        del node
        self._fixed_classes = {}

    def leave_ClassDef(  # noqa: C901 - maintains assignment-group sorting state
        self, original_node: cst.ClassDef
    ) -> None:
        node = original_node
        for child, replacement in self._fixed_classes.items():
            if child is not original_node:
                node = node.deep_replace(child, replacement)

        doc_string = original_node.get_docstring()
        if not doc_string or "@sorted-attributes" not in doc_string:
            return

        replacement_lines: list[LineType] = []
        assign_lines: list[LineType] = []
        changed = False
        safe_to_fix = True

        def _flush_assign_lines() -> None:
            nonlocal changed, safe_to_fix
            if not assign_lines:
                return

            first_line = cst.ensure_type(assign_lines[0], cst.SimpleStatementLine)
            group_leading_lines = tuple(
                line for line in first_line.leading_lines if line.comment is None
            )
            normalized_assign_lines = []
            for line in assign_lines:
                statement_line = cst.ensure_type(line, cst.SimpleStatementLine)
                normalized_assign_lines.append(
                    statement_line.with_changes(
                        leading_lines=tuple(
                            leading
                            for leading in statement_line.leading_lines
                            if leading.comment is not None
                        )
                    )
                )
            sorted_assign_lines = sorted(
                normalized_assign_lines,
                key=self._get_assign_name,
            )
            sorted_assign_lines[0] = sorted_assign_lines[0].with_changes(
                leading_lines=(*group_leading_lines, *sorted_assign_lines[0].leading_lines)
            )
            group_changed = [self._get_assign_name(line) for line in sorted_assign_lines] != [
                self._get_assign_name(line) for line in assign_lines
            ]
            changed = changed or group_changed
            if group_changed and not all(
                self._assignment_is_safe_to_move(line) for line in assign_lines
            ):
                safe_to_fix = False
            replacement_lines.extend(sorted_assign_lines)
            assign_lines.clear()

        for line in node.body.body:
            if self._starts_new_group(line):
                _flush_assign_lines()
            if self._is_sortable_assignment(line):
                assign_lines.append(line)
            else:
                _flush_assign_lines()
                replacement_lines.append(line)

        _flush_assign_lines()
        if not changed:
            return
        replacement = (
            node.with_changes(body=node.body.with_changes(body=replacement_lines))
            if safe_to_fix
            else None
        )
        if replacement is not None:
            self._fixed_classes[original_node] = replacement
        self.report(
            original_node,
            self.MESSAGE,
            replacement=replacement,
        )

    @staticmethod
    def _starts_new_group(line: LineType) -> bool:
        if not isinstance(line, (cst.SimpleStatementLine, cst.BaseCompoundStatement)):
            return False
        return any(empty_line.comment is None for empty_line in line.leading_lines)

    def _is_sortable_assignment(self, line: LineType) -> bool:
        return m.matches(
            line,
            m.SimpleStatementLine(
                body=[
                    m.OneOf(
                        m.Assign(targets=[m.AssignTarget(target=m.Name())]),
                        m.AnnAssign(target=m.Name()),
                    )
                ]
            ),
        )

    def _get_assign_name(self, line: LineType) -> str:
        statement_line = cst.ensure_type(line, cst.SimpleStatementLine)
        statement = statement_line.body[0]
        if isinstance(statement, cst.Assign):
            target = cst.ensure_type(statement.targets[0].target, cst.Name)
        else:
            assign = cst.ensure_type(statement, cst.AnnAssign)
            target = cst.ensure_type(assign.target, cst.Name)
        return target.value

    def _assignment_is_safe_to_move(self, line: LineType) -> bool:
        statement = cst.ensure_type(line, cst.SimpleStatementLine).body[0]
        value = statement.value if isinstance(statement, (cst.Assign, cst.AnnAssign)) else None
        return value is not None and is_static_literal_expression(value)


__all__ = [
    "SortedAttributes",
]
