# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
import libcst.matchers as m
from libcst.helpers import get_full_name_for_node
from libcst.metadata import ParentNodeProvider

from rattle import Invalid, LintRule, Valid

UNNECESSARY_LAMBDA: str = (
    "The lambda that wraps {function} is redundant and can be replaced by the callable."
)


class NoRedundantLambda(LintRule):
    """
    Replace simple lambdas that only forward their arguments to another callable.
    The replacement can change callback signature, arity, or introspection behavior.
    """

    MESSAGE = UNNECESSARY_LAMBDA
    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    VALID = [
        Valid("lambda x: foo(y)"),
        Valid("lambda x: foo(x, y)"),
        Valid("lambda x, y: foo(x)"),
        Valid("lambda *, x: foo(x)"),
        Valid("lambda x = y: foo(x)"),
        Valid("lambda x, y: foo(y, x)"),
        Valid("lambda self: self.func()"),
        Valid("lambda x, y: foo(y=x, x=y)"),
        Valid("lambda x, y, *z: foo(x, y, z)"),
        Valid("lambda x, y, **z: foo(x, y, z)"),
        Valid("lambda: self.func()"),
        Valid("lambda x, y, z: (t + u).math_call(x, y, z)"),
        Valid("lambda x: obj.method(x)"),
        Valid(
            """
            class C:
                callback = lambda x: foo(x)
            """
        ),
    ]
    INVALID = [
        Invalid("lambda x: foo(x)"),
    ]

    @staticmethod
    def _is_simple_parameter_spec(node: cst.Parameters) -> bool:
        if (
            node.star_kwarg is not None
            or len(node.kwonly_params) > 0
            or len(node.posonly_params) > 0
            or not isinstance(node.star_arg, cst.MaybeSentinel)
        ):
            return False

        return all(param.default is None for param in node.params)

    def visit_Lambda(self, node: cst.Lambda) -> None:
        if self._is_in_class_scope(node):
            return

        if m.matches(
            node,
            m.Lambda(
                params=m.MatchIfTrue(self._is_simple_parameter_spec),
                body=m.Call(
                    args=[
                        m.Arg(value=m.Name(value=param.name.value), star="", keyword=None)
                        for param in node.params.params
                    ]
                ),
            ),
        ):
            call = cst.ensure_type(node.body, cst.Call)
            if not isinstance(call.func, cst.Name):
                return

            full_name = get_full_name_for_node(call)
            if full_name is None:
                full_name = "function"

            self.report(
                node,
                UNNECESSARY_LAMBDA.format(function=full_name),
            )

    def _is_in_class_scope(self, node: cst.CSTNode) -> bool:
        parent = self.get_metadata(ParentNodeProvider, node, None)
        while parent is not None:
            if isinstance(parent, cst.ClassDef):
                return True
            if isinstance(parent, (cst.FunctionDef, cst.Lambda)):
                return False
            parent = self.get_metadata(ParentNodeProvider, parent, None)
        return False


__all__ = [
    "NoRedundantLambda",
]
