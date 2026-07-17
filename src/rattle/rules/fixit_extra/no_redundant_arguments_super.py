# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import libcst as cst
import libcst.matchers as m

from rattle import Invalid, LintRule, Valid


class NoRedundantArgumentsSuper(LintRule):
    """Prefer zero-argument super calls."""

    MESSAGE: str = "Call `super()` without arguments."
    REFERENCES = (("PEP 3135", "https://www.python.org/dev/peps/pep-3135/"),)
    VALID = [
        Valid(
            """
            class Foo(Bar):
                def foo(self, bar):
                    super().foo(bar)
            """
        ),
        Valid(
            """
            class Foo(Bar):
                def foo(self, bar):
                    super(Bar, self).foo(bar)
            """
        ),
        Valid(
            """
            class Foo(Bar):
                @classmethod
                def foo(cls, bar):
                    super(Bar, cls).foo(bar)
            """
        ),
        Valid(
            """
            class Foo:
                class InnerBar(Bar):
                    def foo(self, bar):
                        pass

                class InnerFoo(InnerBar):
                    def foo(self, bar):
                        super(InnerBar, self).foo(bar)
            """
        ),
        Valid(
            """
            class Foo(Bar):
                def foo(self, other):
                    super(Foo, other).foo()
            """
        ),
        Valid(
            """
            class Foo(Bar):
                @classmethod
                def foo(cls, other):
                    super(Foo, other).foo()
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            class Foo(Bar):
                def foo(self, bar):
                    super(Foo, self).foo(bar)
            """,
        ),
        Invalid(
            """
            class Foo(Bar):
                @classmethod
                def foo(cls, bar):
                    super(Foo, cls).foo(bar)
            """,
        ),
        Invalid(
            """
            class Foo:
                class InnerFoo(Bar):
                    def foo(self, bar):
                        super(Foo.InnerFoo, self).foo(bar)
            """,
        ),
        Invalid(
            """
            class Foo:
                class InnerFoo(Bar):
                    class InnerInnerFoo(Bar):
                        def foo(self, bar):
                            super(Foo.InnerFoo.InnerInnerFoo, self).foo(bar)
            """,
        ),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.current_classes: list[str] = []
        self.current_first_params: list[str | None] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self.current_classes.append(node.name.value)

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        del original_node
        self.current_classes.pop()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        first_param = None
        params = [*node.params.posonly_params, *node.params.params]
        if params:
            first_param = params[0].name.value
        self.current_first_params.append(first_param)

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        del original_node
        self.current_first_params.pop()

    def leave_Call(self, original_node: cst.Call) -> None:
        current_first_param = self.current_first_params[-1] if self.current_first_params else None
        if current_first_param is None:
            return

        if self.current_classes and m.matches(
            original_node,
            m.Call(
                func=m.Name("super"),
                args=[
                    m.Arg(value=self._build_arg_class_matcher()),
                    m.Arg(value=m.Name(current_first_param)),
                ],
            ),
        ):
            self.report(
                original_node,
                self.MESSAGE,
            )

    def _build_arg_class_matcher(self) -> m.BaseExpressionMatchType:
        matcher: m.BaseExpressionMatchType = m.Name(value=self.current_classes[0])

        # For nested classes, we need to match attributes, so we can target
        # `super(Foo.InnerFoo, self)` for example.
        if len(self.current_classes) > 1:
            for class_name in self.current_classes[1:]:
                matcher = m.Attribute(value=matcher, attr=m.Name(value=class_name))

        return matcher


__all__ = [
    "NoRedundantArgumentsSuper",
]
