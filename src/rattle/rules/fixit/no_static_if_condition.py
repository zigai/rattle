# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


from collections.abc import Sequence

import libcst as cst
import libcst.matchers as m

from rattle import Invalid, LintRule, Valid


class NoStaticIfCondition(LintRule):
    """Discourages ``if`` conditions which evaluate to a static value (e.g. ``or True``, ``and False``, etc)."""

    MESSAGE: str = (
        "Your if condition appears to evaluate to a static value (e.g. `or True`, `and False`). "
        "Please double check this logic and if it is actually temporary debug code."
    )
    VALID = [
        Valid(
            """
            if my_func() or not else_func():
                pass
            """
        ),
        Valid(
            """
            if function_call(True):
                pass
            """
        ),
        Valid(
            """
            # ew who would this???
            def true():
                return False
            if true() and else_call():  # True or False
                pass
            """
        ),
        Valid(
            """
            # ew who would this???
            if False or some_func():
                pass
            """
        ),
        Valid(
            """
            if [*values]:
                pass
            """
        ),
        Valid(
            """
            if {**mapping}:
                pass
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            if True:
                do_something()
            """,
        ),
        Invalid(
            """
            if 1:
                do_something()
            """,
        ),
        Invalid(
            """
            if None:
                do_something()
            """,
        ),
        Invalid(
            """
            if "":
                do_something()
            """,
        ),
        Invalid(
            """
            if 0.0:
                do_something()
            """,
        ),
        Invalid(
            """
            if -1:
                do_something()
            """,
        ),
        Invalid(
            """
            if b"":
                do_something()
            """,
        ),
        Invalid(
            """
            if ...:
                do_something()
            """,
        ),
        Invalid(
            """
            if [*values, sentinel]:
                do_something()
            """,
        ),
        Invalid(
            """
            if {**mapping, "sentinel": sentinel}:
                do_something()
            """,
        ),
        Invalid(
            """
            if crazy_expression or True:
                do_something()
            """,
        ),
        Invalid(
            """
            if crazy_expression and False:
                do_something()
            """,
        ),
        Invalid(
            """
            if crazy_expression and not True:
                do_something()
            """,
        ),
        Invalid(
            """
            if crazy_expression or not False:
                do_something()
            """,
        ),
        Invalid(
            """
            if crazy_expression or (something() or True):
                do_something()
            """,
        ),
        Invalid(
            """
            if crazy_expression and (something() and (not True)):
                do_something()
            """,
        ),
        Invalid(
            """
            if crazy_expression and (something() and (other_func() and not True)):
                do_something()
            """,
        ),
        Invalid(
            """
            if (crazy_expression and (something() and (not True))) or True:
                do_something()
            """,
        ),
        Invalid(
            """
            async def some_func() -> none:
                if (await expression()) and False:
                    pass
            """,
        ),
    ]

    @classmethod
    def _extract_static_bool(cls, node: cst.BaseExpression) -> bool | None:
        if m.matches(node, m.Call()):
            # cannot reason about function calls
            return None

        literal_value = cls._extract_literal_truthiness(node)
        if literal_value is not None:
            return literal_value

        if m.matches(node, m.UnaryOperation(operator=m.Not())):
            unary_node = cst.ensure_type(node, cst.UnaryOperation)
            return cls._negate_static_bool(unary_node.expression)

        if isinstance(node, cst.UnaryOperation) and isinstance(
            node.operator, (cst.Minus, cst.Plus)
        ):
            return cls._extract_static_bool(node.expression)

        if m.matches(node, m.BooleanOperation()):
            return cls._extract_static_bool_from_operation(
                cst.ensure_type(node, cst.BooleanOperation)
            )

        return None

    @staticmethod
    def _extract_literal_truthiness(node: cst.BaseExpression) -> bool | None:
        truthiness: bool | None = None
        if m.matches(node, m.Name("True")):
            truthiness = True
        elif m.matches(node, m.Name("False") | m.Name("None")):
            truthiness = False
        elif isinstance(node, cst.Integer):
            truthiness = int(node.value.replace("_", ""), 0) != 0
        elif isinstance(node, cst.Float):
            truthiness = float(node.value.replace("_", "")) != 0.0
        elif isinstance(node, cst.Imaginary):
            truthiness = complex(node.value.replace("_", "")) != 0
        elif isinstance(node, cst.SimpleString) and isinstance(node.evaluated_value, (bytes, str)):
            truthiness = bool(node.evaluated_value)
        elif isinstance(node, cst.Tuple | cst.List | cst.Set):
            truthiness = NoStaticIfCondition._collection_literal_truthiness(node.elements)
        elif isinstance(node, cst.Dict):
            truthiness = NoStaticIfCondition._dict_literal_truthiness(node.elements)
        elif isinstance(node, cst.Ellipsis):
            truthiness = True

        return truthiness

    @staticmethod
    def _collection_literal_truthiness(
        elements: Sequence[cst.BaseElement],
    ) -> bool | None:
        if not elements:
            return False
        if any(isinstance(element, cst.Element) for element in elements):
            return True

        return None

    @staticmethod
    def _dict_literal_truthiness(
        elements: Sequence[cst.BaseDictElement],
    ) -> bool | None:
        if not elements:
            return False
        if any(isinstance(element, cst.DictElement) for element in elements):
            return True

        return None

    @classmethod
    def _negate_static_bool(cls, node: cst.BaseExpression) -> bool | None:
        sub_value = cls._extract_static_bool(node)
        return None if sub_value is None else not sub_value

    @classmethod
    def _extract_static_bool_from_operation(cls, node: cst.BooleanOperation) -> bool | None:
        left_value = cls._extract_static_bool(node.left)
        right_value = cls._extract_static_bool(node.right)

        if m.matches(node.operator, m.Or()) and (right_value is True or left_value is True):
            return True

        if m.matches(node.operator, m.And()) and (right_value is False or left_value is False):
            return False

        return None

    def visit_If(self, node: cst.If) -> None:
        if self._extract_static_bool(node.test) in {True, False}:
            self.report(node, self.MESSAGE)


__all__ = [
    "NoStaticIfCondition",
]
