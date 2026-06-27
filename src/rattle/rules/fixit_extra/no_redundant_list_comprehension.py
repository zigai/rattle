# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
import libcst.matchers as m
from libcst.metadata import QualifiedName, QualifiedNameProvider, QualifiedNameSource

from rattle import Invalid, LintRule, Valid

UNNECESSARY_LIST_COMPREHENSION: str = (
    "Unnecessary list comprehension inside {func}(). Use a generator expression instead."
)


class NoRedundantListComprehension(LintRule):
    """
    Prefer generator expressions inside ``any()`` and ``all()``. Replacing a list
    comprehension changes eager evaluation into lazy short-circuiting, so side
    effects in later iterations may no longer run.
    """

    MESSAGE = UNNECESSARY_LIST_COMPREHENSION
    SOURCE_PATTERNS = ("any(", "all(")
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)

    VALID = [
        Valid("any(val for val in iterable)"),
        Valid("all(val for val in iterable)"),
        # C407 would complain about these, but we won't
        Valid("frozenset([val for val in iterable])"),
        Valid("max([val for val in iterable])"),
        Valid("min([val for val in iterable])"),
        Valid("sorted([val for val in iterable])"),
        Valid("sum([val for val in iterable])"),
        Valid("tuple([val for val in iterable])"),
        Valid(
            """
            def any(value):
                return value

            any([val for val in iterable])
            """
        ),
    ]
    INVALID = [
        Invalid("any([val for val in iterable])"),
        Invalid("all([val for val in iterable])"),
    ]

    def visit_Call(self, node: cst.Call) -> None:
        # This set excludes frozenset, max, min, sorted, sum, and tuple, which C407 would warn
        # about, because none of those functions short-circuit.
        if m.matches(
            node,
            m.Call(func=m.Name("all") | m.Name("any"), args=[m.Arg(value=m.ListComp())]),
        ):
            call_name = cst.ensure_type(node.func, cst.Name).value
            if not QualifiedNameProvider.has_name(
                self,
                node.func,
                QualifiedName(name=f"builtins.{call_name}", source=QualifiedNameSource.BUILTIN),
            ):
                return
            self.report(
                node,
                UNNECESSARY_LIST_COMPREHENSION.format(func=call_name),
            )


__all__ = [
    "NoRedundantListComprehension",
]
