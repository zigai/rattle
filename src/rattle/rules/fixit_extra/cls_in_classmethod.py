# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import libcst as cst
from libcst.metadata import (
    Assignment,
    QualifiedName,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle import Invalid, LintRule, Valid
from rattle.rules.helpers import has_name_declaration, ordinary_parameters

CLS = "cls"


class RenameTransformer(cst.CSTTransformer):
    def __init__(
        self, names: list[cst.Name | cst.BaseString | cst.Attribute], new_name: str
    ) -> None:
        self.names = names
        self.new_name = new_name

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        # Yes this is linear search. We could potentially create a set out of the list,
        # but in most cases there are so few references to the renamed variable that the
        # overhead of creating a set + computing hashes on lookup would likely outweigh
        # any savings. Did not actually benchmark. This code runs extremely rarely IRL.
        if original_node in self.names:
            return original_node.with_changes(value=self.new_name)
        return updated_node


class UseClsInClassmethod(LintRule):
    """Enforces using ``cls`` as the first argument in a ``@classmethod``."""

    METADATA_DEPENDENCIES = (QualifiedNameProvider, ScopeProvider)
    SOURCE_PATTERNS = ("classmethod",)
    MESSAGE = "When using @classmethod, the first argument must be `cls`."
    VALID = [
        Valid("""
            class foo:
                # classmethod with cls first arg.
                @classmethod
                def cm(cls, a, b, c):
                    pass
            """),
        Valid("""
            class foo:
                # non-classmethod with non-cls first arg.
                def nm(self, a, b, c):
                    pass
            """),
        Valid("""
            class foo:
                # staticmethod with non-cls first arg.
                @staticmethod
                def sm(a):
                    pass
            """),
        Valid("""
            class foo:
                @classmethod
                def cm(cls, /):
                    pass
            """),
    ]
    INVALID = [
        Invalid(
            """
            class foo:
                # No args at all.
                @classmethod
                def cm():
                    pass
            """,
            expected_replacement="""
            class foo:
                # No args at all.
                @classmethod
                def cm(cls):
                    pass
            """,
        ),
        Invalid(
            """
            class foo:
                # Single arg + reference.
                @classmethod
                def cm(a):
                    return a
            """,
            expected_replacement="""
            class foo:
                # Single arg + reference.
                @classmethod
                def cm(cls):
                    return cls
            """,
        ),
        Invalid(
            """
            class foo:
                # Another "cls" exists: do not autofix.
                @classmethod
                def cm(a):
                    cls = 2
            """,
        ),
        Invalid(
            """
            class foo:
                # Multiple args + references.
                @classmethod
                async def cm(a, b):
                    b = a
                    b = a.__name__
            """,
            expected_replacement="""
            class foo:
                # Multiple args + references.
                @classmethod
                async def cm(cls, b):
                    b = cls
                    b = cls.__name__
            """,
        ),
        Invalid(
            """
            class foo:
                # Do not replace in nested scopes.
                @classmethod
                async def cm(a, b):
                    b = a
                    b = lambda _: a.__name__
                    def g():
                        return a.__name__

                    # Same-named vars in sub-scopes should not be replaced.
                    b = [a for a in [1,2,3]]
                    def f(a):
                        return a + 1
            """,
            expected_replacement="""
            class foo:
                # Do not replace in nested scopes.
                @classmethod
                async def cm(cls, b):
                    b = cls
                    b = lambda _: cls.__name__
                    def g():
                        return cls.__name__

                    # Same-named vars in sub-scopes should not be replaced.
                    b = [a for a in [1,2,3]]
                    def f(a):
                        return a + 1
            """,
        ),
        Invalid(
            """
            # Do not replace in surrounding scopes.
            a = 1

            class foo:
                a = 2

                def im(a):
                    a = a

                @classmethod
                def cm(a):
                    a[1] = foo.cm(a=a)
            """,
            expected_replacement="""
            # Do not replace in surrounding scopes.
            a = 1

            class foo:
                a = 2

                def im(a):
                    a = a

                @classmethod
                def cm(cls):
                    cls[1] = foo.cm(a=cls)
            """,
        ),
        Invalid(
            """
            def another_decorator(x): pass

            class foo:
                # Multiple decorators.
                @another_decorator
                @classmethod
                @another_decorator
                async def cm(a, b, c):
                    pass
            """,
            expected_replacement="""
            def another_decorator(x): pass

            class foo:
                # Multiple decorators.
                @another_decorator
                @classmethod
                @another_decorator
                async def cm(cls, b, c):
                    pass
            """,
        ),
        Invalid(
            """
            class foo:
                @classmethod
                def cm(a, /):
                    return a
            """,
            expected_replacement="""
            class foo:
                @classmethod
                def cm(cls, /):
                    return cls
            """,
        ),
        Invalid(
            """
            from builtins import classmethod as cm

            class foo:
                @cm
                def cm(kls):
                    return kls
            """,
            expected_replacement="""
            from builtins import classmethod as cm

            class foo:
                @cm
                def cm(cls):
                    return cls
            """,
        ),
    ]

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if not any(
            QualifiedNameProvider.has_name(
                self,
                decorator.decorator,
                QualifiedName(name="builtins.classmethod", source=QualifiedNameSource.BUILTIN),
            )
            or QualifiedNameProvider.has_name(
                self,
                decorator.decorator,
                QualifiedName(name="builtins.classmethod", source=QualifiedNameSource.IMPORT),
            )
            for decorator in node.decorators
        ):
            return  # If it's not a @classmethod, we are not interested.

        ordered_params = [*node.params.posonly_params, *node.params.params]
        if not ordered_params:
            self._report_missing_positional_parameter(node)
            return

        p0_name = ordered_params[0].name
        if p0_name.value == CLS:
            return  # All good.

        replacement = self._renamed_classmethod(node, p0_name)
        self.report(node, self.MESSAGE, replacement=replacement)

    def _report_missing_positional_parameter(self, node: cst.FunctionDef) -> None:
        if any(param.name.value == CLS for param in ordinary_parameters(node.params)):
            self.report(node, self.MESSAGE)
            return

        new_params = node.params.with_changes(params=(cst.Param(name=cst.Name(value=CLS)),))
        self.report(node, self.MESSAGE, replacement=node.with_changes(params=new_params))

    def _renamed_classmethod(
        self, node: cst.FunctionDef, p0_name: cst.Name
    ) -> cst.FunctionDef | None:

        # Rename all assignments and references of the first param within the
        # function scope, as long as they are done via a Name node.
        # We rely on the parser to correctly derive all
        # assignments and references within the FunctionScope.
        # The Param node's scope is our classmethod's FunctionScope.
        scope = self.get_metadata(ScopeProvider, p0_name, None)
        if not scope:
            # Cannot autofix without scope metadata. Only report in this case.
            # Not sure how to repro+cover this in a unit test...
            # If metadata creation fails, then the whole lint fails, and if it succeeds,
            # then there is valid metadata. But many other lint rule implementations contain
            # a defensive scope None check like this one, so I assume it is necessary.
            return None

        if scope[CLS]:
            # The scope already has another assignment to "cls".
            # Trying to rename the first param to "cls" as well may produce broken code.
            # We should therefore refrain from suggesting an autofix in this case.
            return None

        if has_name_declaration(node.body, CLS):
            return None

        refs: list[cst.Name | cst.Attribute | cst.BaseString] = []
        assignments = scope[p0_name.value]
        for a in assignments:
            if isinstance(a, Assignment):
                assign_node = a.node
                if isinstance(assign_node, cst.Name):
                    refs.append(assign_node)
                elif isinstance(assign_node, cst.Param):
                    refs.append(assign_node.name)
                else:
                    return None
            refs += [r.node for r in a.references]

        replacement = node.visit(RenameTransformer(refs, CLS))
        return replacement if isinstance(replacement, cst.FunctionDef) else None


__all__ = [
    "UseClsInClassmethod",
]
