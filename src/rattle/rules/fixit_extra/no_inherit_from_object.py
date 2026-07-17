# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
from libcst.metadata import QualifiedName, QualifiedNameProvider, QualifiedNameSource

from rattle import CodePosition, CodeRange, Invalid, LintRule, Valid


class NoInheritFromObject(LintRule):
    """
    Python 3 classes inherit from ``object`` implicitly, so an explicit
    ``object`` base class is redundant.
    """

    MESSAGE = "Remove the redundant `object` base class."
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)
    VALID = [
        Valid("class A(something):    pass"),
        Valid(
            """
            class A:
                pass"""
        ),
        Valid(
            """
            class object:
                pass

            class A(object):
                pass
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            class B(object):
                pass""",
            expected_replacement="""
                class B:
                    pass""",
            range=CodeRange(start=CodePosition(1, 0), end=CodePosition(2, 8)),
        ),
        Invalid(
            """
            class B(object, A):
                pass""",
            range=CodeRange(start=CodePosition(1, 0), end=CodePosition(2, 8)),
        ),
    ]

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        new_bases = tuple(
            base
            for base in node.bases
            if not (
                QualifiedNameProvider.has_name(
                    self,
                    base.value,
                    QualifiedName(name="builtins.object", source=QualifiedNameSource.BUILTIN),
                )
                or QualifiedNameProvider.has_name(
                    self,
                    base.value,
                    QualifiedName(name="builtins.object", source=QualifiedNameSource.IMPORT),
                )
            )
        )

        if tuple(node.bases) != new_bases:
            can_fix = (
                len(node.bases) == 1
                and not node.keywords
                and "#" not in cst.Module([]).code_for_node(node)
            )
            if not can_fix:
                self.report(node, self.MESSAGE)
                return
            # reconstruct classdef, removing parens if bases and keywords are empty
            new_classdef = node.with_changes(
                bases=new_bases,
                lpar=cst.MaybeSentinel.DEFAULT,
                rpar=cst.MaybeSentinel.DEFAULT,
            )

            # report warning and autofix
            self.report(node, self.MESSAGE, replacement=new_classdef)


__all__ = [
    "NoInheritFromObject",
]
