# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
import libcst.matchers as m

from rattle import Invalid, LintRule, Valid

LineType = cst.BaseSmallStatement | cst.BaseStatement


class SortedAttributes(LintRule):
    """
    Ever wanted to sort a bunch of class attributes alphabetically?
    Well now it's easy! Just add "@sorted-attributes" in the doc string of
    a class definition and lint will automatically sort all attributes alphabetically.

    Feel free to add other methods and such -- it should only affect class attributes.
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
    MESSAGE: str = "It appears you are using the @sorted-attributes directive and the class variables are unsorted. See the lint autofix suggestion."
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

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        doc_string = node.get_docstring()
        if not doc_string or "@sorted-attributes" not in doc_string:
            return

        replacement_lines: list[LineType] = []
        assign_lines: list[LineType] = []
        changed = False

        def _flush_assign_lines() -> None:
            nonlocal changed
            if not assign_lines:
                return

            sorted_assign_lines = sorted(
                assign_lines,
                key=self._get_assign_name,
            )
            changed = changed or sorted_assign_lines != assign_lines
            replacement_lines.extend(sorted_assign_lines)
            assign_lines.clear()

        for line in node.body.body:
            if self._is_sortable_assignment(line):
                assign_lines.append(line)
            else:
                _flush_assign_lines()
                replacement_lines.append(line)

        _flush_assign_lines()
        if not changed:
            return
        self.report(
            node,
            self.MESSAGE,
            replacement=node.with_changes(body=node.body.with_changes(body=replacement_lines)),
        )

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


__all__ = [
    "SortedAttributes",
]
