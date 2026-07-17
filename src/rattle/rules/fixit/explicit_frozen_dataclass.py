# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
from libcst.metadata import (
    QualifiedName,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle import CodePosition, CodeRange, Invalid, LintRule, Valid
from rattle.rules.helpers import attribute_root_is_imported_module, dotted_name


class ExplicitFrozenDataclass(LintRule):
    """Requires dataclass mutability to be explicit."""

    MESSAGE: str = (
        "Dataclass mutability must be explicit. Add `frozen=True` for immutable "
        "value objects or `frozen=False` when instances are intentionally mutable."
    )
    METADATA_DEPENDENCIES = (QualifiedNameProvider, ScopeProvider)
    SOURCE_PATTERNS = ("dataclass",)
    VALID = [
        Valid(
            """
            @some_other_decorator
            class Cls: pass
            """
        ),
        Valid(
            """
            from dataclasses import dataclass
            @dataclass(frozen=False)
            class Cls: pass
            """
        ),
        Valid(
            """
            import dataclasses
            @dataclasses.dataclass(frozen=False)
            class Cls: pass
            """
        ),
        Valid(
            """
            import dataclasses as dc
            @dc.dataclass(frozen=False)
            class Cls: pass
            """
        ),
        Valid(
            """
            from dataclasses import dataclass as dc
            @dc(frozen=False)
            class Cls: pass
            """
        ),
        Valid(
            """
            from dataclasses import dataclass
            dc = dataclass
            @dc(frozen=True)
            class Cls: pass
            """
        ),
        Valid(
            """
            from dataclasses import dataclass
            dc = dataclass
            def dc(cls):
                return cls
            @dc
            class Cls: pass
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            from dataclasses import dataclass
            @some_unrelated_decorator
            @dataclass  # not called as a function
            @another_unrelated_decorator
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(3, 0), end=CodePosition(3, 10)),
        ),
        Invalid(
            """
            from dataclasses import dataclass
            @dataclass()  # called as a function, no kwargs
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 12)),
        ),
        Invalid(
            """
            from dataclasses import dataclass
            @dataclass(other_kwarg=False)
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 29)),
        ),
        Invalid(
            """
            import dataclasses
            @dataclasses.dataclass
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 22)),
        ),
        Invalid(
            """
            import dataclasses
            @dataclasses.dataclass()
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 24)),
        ),
        Invalid(
            """
            import dataclasses
            @dataclasses.dataclass(other_kwarg=False)
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 41)),
        ),
        Invalid(
            """
            from dataclasses import dataclass as dc
            @dc
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 3)),
        ),
        Invalid(
            """
            from dataclasses import dataclass as dc
            @dc()
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 5)),
        ),
        Invalid(
            """
            from dataclasses import dataclass as dc
            @dc(other_kwarg=False)
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 22)),
        ),
        Invalid(
            """
            import dataclasses as dc
            @dc.dataclass
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 13)),
        ),
        Invalid(
            """
            import dataclasses as dc
            @dc.dataclass()
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 15)),
        ),
        Invalid(
            """
            import dataclasses as dc
            @dc.dataclass(other_kwarg=False)
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 32)),
        ),
        Invalid(
            """
            from dataclasses import *
            @dataclass
            class Cls: pass
            """,
        ),
        Invalid(
            """
            from dataclasses import dataclass
            dc = dataclass
            @dc
            class Cls: pass
            """,
        ),
        Invalid(
            """
            from dataclasses import dataclass
            dc = dataclass
            dc2 = dc
            @dc2
            class Cls: pass
            """,
        ),
        Invalid(
            """
            from dataclasses import dataclass
            dc = dc2 = dataclass
            @dc2
            class Cls: pass
            """,
        ),
    ]

    def __init__(self) -> None:
        super().__init__()

        self._dataclass_alias_nodes: set[cst.CSTNode] = set()
        self._has_dataclasses_star_import = False

    def visit_Module(self, node: cst.Module) -> None:
        del node

        self._dataclass_alias_nodes = set()
        self._has_dataclasses_star_import = False

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node

        self._dataclass_alias_nodes = set()
        self._has_dataclasses_star_import = False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if dotted_name(node.module) == "dataclasses" and isinstance(node.names, cst.ImportStar):
            self._has_dataclasses_star_import = True

    def visit_Assign(self, node: cst.Assign) -> None:
        if self._expression_is_imported_dataclass(
            node.value
        ) or self._expression_is_dataclass_alias(node.value):
            for assign_target in node.targets:
                if isinstance(assign_target.target, cst.Name):
                    self._dataclass_alias_nodes.add(assign_target.target)
        else:
            for assign_target in node.targets:
                if isinstance(assign_target.target, cst.Name):
                    self._dataclass_alias_nodes.discard(assign_target.target)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if not isinstance(node.target, cst.Name) or node.value is None:
            return

        if self._expression_is_imported_dataclass(
            node.value
        ) or self._expression_is_dataclass_alias(node.value):
            self._dataclass_alias_nodes.add(node.target)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        for d in node.decorators:
            decorator = d.decorator
            if self._is_dataclass_decorator(decorator):
                args = decorator.args if isinstance(decorator, cst.Call) else ()

                if not any(
                    isinstance(arg.keyword, cst.Name) and arg.keyword.value == "frozen"
                    for arg in args
                ):
                    self.report(d, self.MESSAGE)

    def _is_dataclass_decorator(self, expression: cst.BaseExpression) -> bool:
        callable_expression = expression.func if isinstance(expression, cst.Call) else expression
        return (
            self._expression_is_imported_dataclass(expression)
            or self._expression_is_imported_dataclass(callable_expression)
            or self._expression_is_dataclass_alias(callable_expression)
            or self._expression_is_star_imported_dataclass(callable_expression)
        )

    def _expression_is_imported_dataclass(self, expression: cst.BaseExpression) -> bool:
        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        imported_name = QualifiedName(
            name="dataclasses.dataclass", source=QualifiedNameSource.IMPORT
        )
        if imported_name not in qualified_names:
            return False
        if not any(name.source is QualifiedNameSource.LOCAL for name in qualified_names):
            return True

        return attribute_root_is_imported_module(self, expression, {"dataclasses"})

    def _expression_is_dataclass_alias(self, expression: cst.BaseExpression) -> bool:
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
            and assignment_node in self._dataclass_alias_nodes
            for assignment in reference_assignments
        )

    def _expression_is_star_imported_dataclass(self, expression: cst.BaseExpression) -> bool:
        if not self._has_dataclasses_star_import:
            return False
        if not isinstance(expression, cst.Name) or expression.value != "dataclass":
            return False

        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        return not qualified_names


__all__ = [
    "ExplicitFrozenDataclass",
]
