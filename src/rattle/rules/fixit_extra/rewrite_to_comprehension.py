# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import libcst as cst
import libcst.matchers as m
from libcst.metadata import QualifiedName, QualifiedNameProvider, QualifiedNameSource

from rattle import Invalid, LintRule, Valid

UNNECESSARY_GENERATOR: str = "Replace this {func}() call with the equivalent comprehension."
UNNECESSARY_LIST_COMPREHENSION: str = (
    "Replace the list comprehension inside {func}() with the equivalent comprehension."
)


class RewriteToComprehension(LintRule):
    """Prefer comprehensions over unnecessary collection constructor calls."""

    NAME = "use-comprehension"
    MESSAGE = UNNECESSARY_GENERATOR
    SOURCE_PATTERNS = ("list(", "set(", "dict(")
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)

    VALID = [
        Valid("[val for val in iterable]"),
        Valid("{val for val in iterable}"),
        Valid("{val: val+1 for val in iterable}"),
        # A function call is valid if the elt is a function that returns a tuple.
        Valid("dict(line.strip().split('=', 1) for line in attr_file)"),
        Valid("""
            def list(value):
                return value

            list(val for val in iterable)
            """),
    ]

    INVALID = [
        Invalid(
            "list(val for val in iterable)",
        ),
        # Nested list comprehenstion
        Invalid(
            "list(val for row in matrix for val in row)",
        ),
        Invalid(
            "set(val for val in iterable)",
        ),
        Invalid(
            "dict((x, f(x)) for val in iterable)",
        ),
        Invalid(
            "dict((x, y) for y, x in iterable)",
        ),
        Invalid(
            "dict([val, val+1] for val in iterable)",
        ),
        Invalid(
            'dict((x["name"], json.loads(x["data"])) for x in responses)',
        ),
        # Nested dict comprehension
        Invalid(
            "dict((k, v) for k, v in iter for iter in iters)",
        ),
        Invalid(
            "set([val for val in iterable])",
        ),
        Invalid(
            "dict([[val, val+1] for val in iterable])",
        ),
        Invalid(
            "dict([(x, f(x)) for x in foo])",
        ),
        Invalid(
            "dict([(x, y) for y, x in iterable])",
        ),
        Invalid(
            "set([val for row in matrix for val in row])",
        ),
    ]

    def visit_Call(self, node: cst.Call) -> None:
        if m.matches(
            node,
            m.Call(
                func=m.Name("list") | m.Name("set") | m.Name("dict"),
                args=[m.Arg(value=m.GeneratorExp() | m.ListComp())],
            ),
        ):
            call_name = cst.ensure_type(node.func, cst.Name).value
            if not QualifiedNameProvider.has_name(
                self,
                node.func,
                QualifiedName(name=f"builtins.{call_name}", source=QualifiedNameSource.BUILTIN),
            ):
                return

            exp: cst.GeneratorExp | cst.ListComp
            if m.matches(node.args[0].value, m.GeneratorExp()):
                exp = cst.ensure_type(node.args[0].value, cst.GeneratorExp)
                message_formatter = UNNECESSARY_GENERATOR
            else:
                exp = cst.ensure_type(node.args[0].value, cst.ListComp)
                message_formatter = UNNECESSARY_LIST_COMPREHENSION

            if call_name == "dict" and not m.matches(
                exp.elt,
                m.Tuple(elements=[m.Element(), m.Element()])
                | m.List(elements=[m.Element(), m.Element()]),
            ):
                return

            self.report(node, message_formatter.format(func=call_name))


__all__ = [
    "RewriteToComprehension",
]
