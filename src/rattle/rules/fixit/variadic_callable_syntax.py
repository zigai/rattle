# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
import libcst.matchers as m
from libcst.metadata import (
    QualifiedName,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle import Invalid, LintRule, Valid
from rattle.rules.helpers import attribute_root_is_imported_module, dotted_name


class VariadicCallableSyntax(LintRule):
    """Prefer Callable[..., T] for callable types with arbitrary parameters."""

    NAME = "use-callable-ellipsis"
    MESSAGE = "Use Callable[..., T] instead of Callable[[...], T]."

    METADATA_DEPENDENCIES = (QualifiedNameProvider, ScopeProvider)
    SOURCE_PATTERNS = ("Callable",)
    VALID = [
        Valid(
            """
            from typing import Callable
            x: Callable[[int], int]
            """
        ),
        Valid(
            """
            from typing import Callable
            x: Callable[[int, int, ...], int]
            """
        ),
        Valid(
            """
            from typing import Callable
            x: Callable
            """
        ),
        Valid(
            """
            from typing import Callable as C
            x: C[..., int] = ...
            """
        ),
        Valid(
            """
            from typing import Callable
            def foo(bar: Optional[Callable[..., int]]) -> Callable[..., int]:
                ...
            """
        ),
        Valid(
            """
            import typing as t
            x: t.Callable[..., int] = ...
            """
        ),
        Valid(
            """
            from typing import Callable
            x: Callable[..., int] = ...
            """
        ),
        Valid(
            """
            from typing import Callable
            C = Callable

            class C:
                def __class_getitem__(cls, item):
                    return cls

            x: C[[...], int] = ...
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            from typing import Callable
            x: Callable[[...], int] = ...
            """,
            expected_replacement="""
            from typing import Callable
            x: Callable[..., int] = ...
            """,
        ),
        Invalid(
            """
            import typing as t
            x: t.Callable[[...], int] = ...
            """,
            expected_replacement="""
            import typing as t
            x: t.Callable[..., int] = ...
            """,
        ),
        Invalid(
            """
            from typing import Callable as C
            x: C[[...], int] = ...
            """,
            expected_replacement="""
            from typing import Callable as C
            x: C[..., int] = ...
            """,
        ),
        Invalid(
            """
            from typing import Callable
            def foo(bar: Optional[Callable[[...], int]]) -> Callable[[...], int]:
                ...
            """,
            expected_replacement="""
            from typing import Callable
            def foo(bar: Optional[Callable[..., int]]) -> Callable[..., int]:
                ...
            """,
        ),
        Invalid(
            """
            from collections.abc import Callable
            x: Callable[[...], int] = ...
            """,
            expected_replacement="""
            from collections.abc import Callable
            x: Callable[..., int] = ...
            """,
        ),
        Invalid(
            """
            from typing import Callable
            C = Callable
            x: C[[...], int] = ...
            """,
            expected_replacement="""
            from typing import Callable
            C = Callable
            x: C[..., int] = ...
            """,
        ),
        Invalid(
            """
            from typing import Callable
            C = OtherC = Callable
            x: OtherC[[...], int] = ...
            """,
            expected_replacement="""
            from typing import Callable
            C = OtherC = Callable
            x: OtherC[..., int] = ...
            """,
        ),
        Invalid(
            """
            from typing import *
            x: Callable[[...], int] = ...
            """,
            expected_replacement="""
            from typing import *
            x: Callable[..., int] = ...
            """,
        ),
    ]

    _QUALIFIED_CALLABLES = frozenset(
        {
            QualifiedName(name="typing.Callable", source=QualifiedNameSource.IMPORT),
            QualifiedName(
                name="typing_extensions.Callable",
                source=QualifiedNameSource.IMPORT,
            ),
            QualifiedName(
                name="collections.abc.Callable",
                source=QualifiedNameSource.IMPORT,
            ),
        }
    )

    def __init__(self) -> None:
        super().__init__()

        self._callable_alias_nodes: set[cst.CSTNode] = set()
        self._star_import_modules: set[str] = set()

    def visit_Module(self, node: cst.Module) -> None:
        del node

        self._callable_alias_nodes = set()
        self._star_import_modules = set()

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._callable_alias_nodes = set()
        self._star_import_modules = set()

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if not isinstance(node.names, cst.ImportStar):
            return

        module_name = dotted_name(node.module)
        if module_name in {"collections.abc", "typing", "typing_extensions"}:
            self._star_import_modules.add(module_name)

    def visit_Assign(self, node: cst.Assign) -> None:
        if self._is_callable_annotation(node.value):
            for assign_target in node.targets:
                if isinstance(assign_target.target, cst.Name):
                    self._callable_alias_nodes.add(assign_target.target)
        else:
            for assign_target in node.targets:
                if isinstance(assign_target.target, cst.Name):
                    self._callable_alias_nodes.discard(assign_target.target)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if not isinstance(node.target, cst.Name) or node.value is None:
            return

        if self._is_callable_annotation(node.value):
            self._callable_alias_nodes.add(node.target)

    def visit_Subscript(self, node: cst.Subscript) -> None:
        if not self._is_callable_annotation(node.value):
            return
        if len(node.slice) == 2 and m.matches(
            node.slice[0],
            m.SubscriptElement(slice=m.Index(value=m.List(elements=[m.Element(m.Ellipsis())]))),
        ):
            first_slice = node.slice[0]
            if not isinstance(first_slice.slice, cst.Index):
                return
            list_expression = first_slice.slice.value
            if m.findall(list_expression, m.Comment()):
                self.report(node, self.MESSAGE)
                return

            replacement = node.with_changes(
                slice=(
                    first_slice.with_changes(slice=cst.Index(cst.Ellipsis())),
                    *node.slice[1:],
                )
            )
            self.report(node, self.MESSAGE, replacement=replacement)

    def _is_callable_annotation(self, expression: cst.BaseExpression) -> bool:
        return (
            self._is_imported_callable(expression)
            or self._is_callable_alias(expression)
            or self._is_star_imported_callable(expression)
        )

    def _is_imported_callable(self, expression: cst.BaseExpression) -> bool:
        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        matching_names = self._QUALIFIED_CALLABLES.intersection(qualified_names)
        if not matching_names:
            return False
        if not any(name.source is QualifiedNameSource.LOCAL for name in qualified_names):
            return True

        module_names = {name.name.rpartition(".")[0] for name in matching_names}
        return attribute_root_is_imported_module(self, expression, module_names)

    def _is_callable_alias(self, expression: cst.BaseExpression) -> bool:
        if not isinstance(expression, cst.Name):
            return False

        scope = self.get_metadata(ScopeProvider, expression, None)
        if scope is None:
            return False

        try:
            assignments = scope[expression.value]
        except KeyError:
            return False

        reference_assignments = [
            assignment
            for assignment in assignments
            if any(access.node is expression for access in assignment.references)
        ]
        return bool(reference_assignments) and all(
            (assignment_node := getattr(assignment, "node", None)) is not None
            and assignment_node in self._callable_alias_nodes
            for assignment in reference_assignments
        )

    def _is_star_imported_callable(self, expression: cst.BaseExpression) -> bool:
        if not self._star_import_modules:
            return False
        if not isinstance(expression, cst.Name) or expression.value != "Callable":
            return False

        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        return not qualified_names


__all__ = [
    "VariadicCallableSyntax",
]
