# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


from collections.abc import Sequence

import libcst as cst
import libcst.matchers as m

from rattle import Invalid, LintRule, Valid


class NoStaticIfCondition(LintRule):
    """Detect ``if`` conditions that appear to evaluate to a constant value."""

    MESSAGE: str = (
        "This `if` condition appears constant; verify the logic and remove any temporary "
        "debug clause."
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

        truthiness = cls._extract_literal_truthiness(node)
        if m.matches(node, m.UnaryOperation(operator=m.Not())):
            unary_node = cst.ensure_type(node, cst.UnaryOperation)
            truthiness = cls._negate_static_bool(unary_node.expression)
        elif isinstance(node, cst.UnaryOperation) and isinstance(
            node.operator, (cst.Minus, cst.Plus)
        ):
            truthiness = cls._extract_static_bool(node.expression)
        elif m.matches(node, m.BooleanOperation()):
            truthiness = cls._extract_static_bool_from_operation(
                cst.ensure_type(node, cst.BooleanOperation)
            )
        elif isinstance(node, cst.NamedExpr):
            truthiness = cls._extract_static_bool(node.value)
        elif isinstance(node, (cst.GeneratorExp, cst.Lambda)):
            truthiness = True

        return truthiness

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
        elif isinstance(node, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)):
            truthiness = NoStaticIfCondition._string_literal_truthiness(node)
        elif isinstance(node, cst.Tuple | cst.List | cst.Set):
            truthiness = NoStaticIfCondition._collection_literal_truthiness(node.elements)
        elif isinstance(node, cst.Dict):
            truthiness = NoStaticIfCondition._dict_literal_truthiness(node.elements)
        elif isinstance(node, cst.Ellipsis):
            truthiness = True

        return truthiness

    @classmethod
    def _string_literal_truthiness(
        cls,
        node: cst.SimpleString | cst.ConcatenatedString | cst.FormattedString,
    ) -> bool | None:
        if isinstance(node, cst.SimpleString):
            value = node.evaluated_value
            return bool(value) if isinstance(value, (bytes, str)) else None
        if isinstance(node, cst.ConcatenatedString):
            return cls._concatenated_string_truthiness(node)
        return cls._formatted_string_truthiness(node)

    @classmethod
    def _concatenated_string_truthiness(cls, node: cst.ConcatenatedString) -> bool | None:
        values = (
            cls._extract_static_bool(node.left),
            cls._extract_static_bool(node.right),
        )
        if True in values:
            return True
        if values == (False, False):
            return False
        return None

    @staticmethod
    def _formatted_string_truthiness(node: cst.FormattedString) -> bool | None:
        if not node.parts:
            return False
        if any(isinstance(part, cst.FormattedStringText) and part.value for part in node.parts):
            return True
        return None

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

        if left_value is not None and right_value is not None:
            if isinstance(node.operator, cst.Or):
                return left_value or right_value
            if isinstance(node.operator, cst.And):
                return left_value and right_value

        return None

    def visit_If(self, node: cst.If) -> None:
        if self._extract_static_bool(node.test) in {True, False}:
            self.report(node, self.MESSAGE)


__all__ = [
    "NoStaticIfCondition",
]
