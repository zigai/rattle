# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from collections.abc import Sequence

import libcst as cst
import libcst.matchers as m
from libcst.metadata import QualifiedName, QualifiedNameProvider, QualifiedNameSource

from rattle import Invalid, LintRule, Valid

UNNECESSARY_LITERAL: str = "Replace this {func}() call with the equivalent collection literal."
UNNCESSARY_CALL: str = "Replace {func}() with the equivalent empty collection literal."


class RewriteToLiteral(LintRule):
    """Prefer collection literals over unnecessary constructor calls."""

    NAME = "use-literal"
    MESSAGE = UNNECESSARY_LITERAL
    SOURCE_PATTERNS = ("tuple(", "list(", "set(", "dict(")
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)

    VALID = [
        Valid("(1, 2)"),
        Valid("()"),
        Valid("[1, 2]"),
        Valid("[]"),
        Valid("{1, 2}"),
        Valid("set()"),
        Valid("{1: 2, 3: 4}"),
        Valid("{}"),
        Valid(
            """
            def list():
                return 1

            list()
            """
        ),
    ]

    INVALID = [
        Invalid("tuple([1, 2])", expected_replacement="(1, 2)"),
        Invalid("tuple((1, 2))", expected_replacement="(1, 2)"),
        Invalid("tuple([])", expected_replacement="()"),
        Invalid("list([1, 2, 3])", expected_replacement="[1, 2, 3]"),
        Invalid("list((1, 2, 3))", expected_replacement="[1, 2, 3]"),
        Invalid("list([])", expected_replacement="[]"),
        Invalid("set([1, 2, 3])", expected_replacement="{1, 2, 3}"),
        Invalid("set((1, 2, 3))", expected_replacement="{1, 2, 3}"),
        Invalid("set([])", expected_replacement="set()"),
        Invalid(
            "dict([(1, 2), (3, 4)])",
            expected_replacement="{1: 2, 3: 4}",
        ),
        Invalid(
            "dict(((1, 2), (3, 4)))",
            expected_replacement="{1: 2, 3: 4}",
        ),
        Invalid(
            "dict([[1, 2], [3, 4], [5, 6]])",
            expected_replacement="{1: 2, 3: 4, 5: 6}",
        ),
        Invalid("dict([])", expected_replacement="{}"),
        Invalid("tuple()", expected_replacement="()"),
        Invalid("list()", expected_replacement="[]"),
        Invalid("dict()", expected_replacement="{}"),
    ]

    def _dict_element_from_pair(self, element: cst.BaseElement) -> cst.DictElement:
        pair = cst.ensure_type(element, cst.Element)
        pair_value = cst.ensure_type(
            pair.value, cst.Tuple if isinstance(pair.value, cst.Tuple) else cst.List
        )
        key = cst.ensure_type(pair_value.elements[0], cst.Element).value
        value = cst.ensure_type(pair_value.elements[1], cst.Element).value
        return cst.DictElement(key, value, comma=pair.comma)

    def visit_Call(self, node: cst.Call) -> None:
        if self._matches_literal_call(node):
            exp = cst.ensure_type(node, cst.Call)
            if exp.args and not self._has_plain_positional_argument(exp.args[0]):
                return
            call_name = cst.ensure_type(exp.func, cst.Name).value
            if not QualifiedNameProvider.has_name(
                self,
                exp.func,
                QualifiedName(name=f"builtins.{call_name}", source=QualifiedNameSource.BUILTIN),
            ):
                return

            # If this is a empty call, it's an Unnecessary Call where we rewrite the call
            # to literal, except set().
            elements: Sequence[cst.BaseElement]
            if not exp.args:
                elements = []
                message_formatter = UNNCESSARY_CALL
            else:
                arg = exp.args[0].value
                if isinstance(arg, (cst.List, cst.Tuple)):
                    elements = arg.elements
                else:
                    raise ValueError(f"Unexpected {type(arg)}")
                message_formatter = UNNECESSARY_LITERAL

            new_node = self._literal_replacement(exp, call_name, elements)
            if new_node is None:
                return

            self.report(
                node,
                message_formatter.format(func=call_name),
                replacement=node.deep_replace(node, new_node),
            )

    def _has_plain_positional_argument(self, argument: cst.Arg) -> bool:
        return argument.keyword is None and not argument.star

    def _literal_replacement(
        self,
        call: cst.Call,
        call_name: str,
        elements: Sequence[cst.BaseElement],
    ) -> cst.BaseExpression | None:
        if call_name in {"tuple", "list"}:
            return (
                cst.Tuple(elements=elements)
                if call_name == "tuple"
                else cst.List(elements=elements)
            )
        if call_name == "set":
            if not elements:
                return cst.Call(func=cst.Name("set"))
            return cst.Set(elements=elements)
        if not elements:
            return cst.Dict(elements=[])
        pairs_matcher = m.ZeroOrMore(
            m.Element(m.Tuple(elements=[m.Element(), m.Element()]))
            | m.Element(m.List(elements=[m.Element(), m.Element()]))
        )
        if not m.matches(
            call.args[0].value,
            m.Tuple(elements=[pairs_matcher]) | m.List(elements=[pairs_matcher]),
        ):
            return None
        return cst.Dict(elements=[self._dict_element_from_pair(element) for element in elements])

    def _matches_literal_call(self, node: cst.Call) -> bool:
        return m.matches(
            node,
            m.Call(
                func=m.Name("tuple") | m.Name("list") | m.Name("set") | m.Name("dict"),
                args=[m.Arg(value=m.List() | m.Tuple())],
            ),
        ) or m.matches(
            node,
            m.Call(func=m.Name("tuple") | m.Name("list") | m.Name("dict"), args=[]),
        )


__all__ = [
    "RewriteToLiteral",
]
