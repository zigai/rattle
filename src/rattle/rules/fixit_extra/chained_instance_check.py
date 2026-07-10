# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import libcst as cst
import libcst.matchers as m
from libcst.metadata import QualifiedName, QualifiedNameProvider, QualifiedNameSource

from rattle import Invalid, LintRule, Valid

_ISINSTANCE_NAMES = (
    QualifiedName(name="builtins.isinstance", source=QualifiedNameSource.BUILTIN),
    QualifiedName(name="builtins.isinstance", source=QualifiedNameSource.IMPORT),
)


@dataclass
class IsinstanceTargetInfo:
    func: cst.BaseExpression
    matches: list[cst.BaseExpression]


class CollapseIsinstanceChecks(LintRule):
    """Combine repeated ``isinstance`` checks by passing a tuple of types."""

    MESSAGE: str = (
        "Multiple isinstance calls with the same target but "
        "different types can be collapsed into a single call "
        "with a tuple of types."
    )

    METADATA_DEPENDENCIES = (QualifiedNameProvider,)
    SOURCE_PATTERNS = ("isinstance",)

    VALID = [
        Valid("foo() or foo()"),
        Valid("foo(x, y) or foo(x, z)"),
        Valid("foo(x, y) or foo(x, z) or foo(x, q)"),
        Valid("isinstance() or isinstance()"),
        Valid("isinstance(x) or isinstance(x)"),
        Valid("isinstance(x, y) or isinstance(x)"),
        Valid("isinstance(x) or isinstance(x, y)"),
        Valid("isinstance(x, y) or isinstance(t, y)"),
        Valid("isinstance(f(), A) or isinstance(f(), B)"),
        Valid("isinstance(x, y) and isinstance(x, z)"),
        Valid("isinstance(x, y) or isinstance(x, (z, q))"),
        Valid("isinstance(x, (y, z)) or isinstance(x, q)"),
        Valid("isinstance(x, a) or isinstance(y, b) or isinstance(z, c)"),
        Valid(
            """
            def foo():
                def isinstance(x, y):
                    return _foo_bar(x, y)
                if isinstance(x, y) or isinstance(x, z):
                    print("foo")
            """
        ),
    ]
    INVALID = [
        Invalid(
            "isinstance(x, y) or isinstance(x, z)",
            expected_replacement="isinstance(x, (y, z))",
        ),
        Invalid(
            "isinstance(x, y) or isinstance(x, z) or isinstance(x, q)",
            expected_replacement="isinstance(x, (y, z, q))",
        ),
        Invalid(
            "something or isinstance(x, y) or isinstance(x, z) or another",
            expected_replacement="something or isinstance(x, (y, z)) or another",
        ),
        Invalid(
            "isinstance(x, y) or isinstance(x, z) or isinstance(x, q) or isinstance(x, w)",
            expected_replacement="isinstance(x, (y, z, q, w))",
        ),
        Invalid(
            "isinstance(x, a) or isinstance(x, b) or isinstance(y, c) or isinstance(y, d)",
            expected_replacement="isinstance(x, (a, b)) or isinstance(y, (c, d))",
        ),
        Invalid(
            "isinstance(x, a) or isinstance(x, b) or isinstance(y, c) or isinstance(y, d) "
            "or isinstance(z, e)",
            expected_replacement="isinstance(x, (a, b)) or isinstance(y, (c, d)) or isinstance(z, e)",
        ),
        Invalid(
            "isinstance(x, a) or isinstance(x, b) or isinstance(y, c) or isinstance(y, d) "
            "or isinstance(z, e) or isinstance(q, f) or isinstance(q, g) or isinstance(q, h)",
            expected_replacement=(
                "isinstance(x, (a, b)) or isinstance(y, (c, d)) or isinstance(z, e)"
                " or isinstance(q, (f, g, h))"
            ),
        ),
        Invalid(
            """
            import builtins

            builtins.isinstance(x, A) or builtins.isinstance(x, B)
            """,
            expected_replacement="""
            import builtins

            builtins.isinstance(x, (A, B))
            """,
        ),
        Invalid(
            """
            from builtins import isinstance as check

            check(x, A) or check(x, B)
            """,
            expected_replacement="""
            from builtins import isinstance as check

            check(x, (A, B))
            """,
        ),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.seen_boolean_operations: set[cst.BooleanOperation] = set()

    def visit_BooleanOperation(self, node: cst.BooleanOperation) -> None:
        if node in self.seen_boolean_operations:
            return None

        stack = tuple(self.unwrap(node))
        operands, targets = self.collect_targets(stack)

        # If nothing gets collapsed, just exit from this short-path
        if len(operands) == len(stack):
            return None

        replacement = None
        for operand in operands:
            if operand in targets:
                target_info = targets[operand]
                call_func = target_info.func
                matches = target_info.matches
                if len(matches) == 1:
                    arg = cst.Arg(value=matches[0])
                else:
                    arg = cst.Arg(cst.Tuple([cst.Element(match) for match in matches]))
                operand = cst.Call(call_func, [cst.Arg(operand), arg])

            if replacement is None:
                replacement = operand
            else:
                replacement = cst.BooleanOperation(
                    left=replacement, right=operand, operator=cst.Or()
                )

        if replacement is not None:
            self.report(node, self.MESSAGE, replacement=replacement)

    def unwrap(self, node: cst.BaseExpression) -> Iterator[cst.BaseExpression]:
        if m.matches(node, m.BooleanOperation(operator=m.Or())):
            bool_op = cst.ensure_type(node, cst.BooleanOperation)
            self.seen_boolean_operations.add(bool_op)
            yield from self.unwrap(bool_op.left)
            yield bool_op.right
        else:
            yield node

    def collect_targets(
        self, stack: tuple[cst.BaseExpression, ...]
    ) -> tuple[list[cst.BaseExpression], dict[cst.BaseExpression, IsinstanceTargetInfo]]:
        targets: dict[cst.BaseExpression, IsinstanceTargetInfo] = {}
        operands = []

        for operand in stack:
            if m.matches(operand, m.Call(func=m.DoNotCare(), args=[m.Arg(), m.Arg(~m.Tuple())])):
                call = cst.ensure_type(operand, cst.Call)
                if not any(
                    QualifiedNameProvider.has_name(self, call, qualified_name)
                    for qualified_name in _ISINSTANCE_NAMES
                ):
                    operands.append(operand)
                    continue

                target, match = call.args[0].value, call.args[1].value
                if not self.is_safe_target(target):
                    operands.append(operand)
                    continue

                for possible_target, matches in targets.items():
                    if target.deep_equals(possible_target):
                        matches.matches.append(match)
                        break
                else:
                    operands.append(target)
                    targets[target] = IsinstanceTargetInfo(func=call.func, matches=[match])
            else:
                operands.append(operand)

        return operands, targets

    def is_safe_target(self, target: cst.BaseExpression) -> bool:
        # Re-evaluating arbitrary expressions can change semantics. Restrict collapsing
        # to plain names, where repeated evaluation is safe.
        return isinstance(target, cst.Name)


__all__ = [
    "CollapseIsinstanceChecks",
]
