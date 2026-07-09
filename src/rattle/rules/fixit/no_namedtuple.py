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

from rattle import Invalid, LintRule, Valid
from rattle.rules.helpers import dotted_name


class NoNamedTuple(LintRule):
    """
    Prefer ``dataclasses.dataclass`` over ``NamedTuple`` when tuple compatibility is
    not required. Dataclasses are not tuple-compatible, so converting public
    ``NamedTuple`` APIs can break unpacking, indexing, equality, and callers that
    expect tuple instances.
    """

    MESSAGE: str = (
        "NamedTuple can often be replaced with @dataclass, but dataclasses are not "
        "tuple-compatible; check callers before converting."
    )
    REFERENCES = (
        ("PEP 557", "https://www.python.org/dev/peps/pep-0557"),
        (
            "benchmark",
            "https://medium.com/@jacktator/dataclass-vs-namedtuple-vs-object-for-performance-optimization-in-python-691e234253b9",
        ),
    )
    METADATA_DEPENDENCIES = (QualifiedNameProvider, ScopeProvider)
    SOURCE_PATTERNS = ("NamedTuple", "namedtuple")

    VALID = [
        Valid("""
            @dataclass(frozen=True)
            class Foo:
                pass
            """),
        Valid("""
            @dataclass(frozen=False)
            class Foo:
                pass
            """),
        Valid("""
            class Foo:
                pass
            """),
        Valid("""
            class Foo(SomeOtherBase):
                pass
            """),
        Valid("""
            @some_other_decorator
            class Foo:
                pass
            """),
        Valid("""
            @some_other_decorator
            class Foo(SomeOtherBase):
                pass
            """),
        Valid("""
            from typing import NamedTuple as NT

            Other = NT
            """),
    ]
    INVALID = [
        Invalid(
            code="""
            from typing import NamedTuple

            class Foo(NamedTuple):
                pass
            """,
        ),
        Invalid(
            code="""
            from typing_extensions import NamedTuple

            class Foo(NamedTuple):
                pass
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple as NT

            class Foo(NT):
                pass
            """,
        ),
        Invalid(
            code="""
            import typing as typ

            class Foo(typ.NamedTuple):
                pass
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple

            class Foo(NamedTuple, AnotherBase, YetAnotherBase):
                pass
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple

            class OuterClass(SomeBase):
                class InnerClass(NamedTuple):
                    pass
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple

            @some_other_decorator
            class Foo(NamedTuple):
                pass
            """,
        ),
        Invalid(
            code="""
            from dataclasses import dataclass
            from typing import NamedTuple

            class Foo(NamedTuple):
                pass
            """,
        ),
        Invalid(
            code="""
            import dataclasses as dc
            from typing import NamedTuple

            class Foo(NamedTuple):
                pass
            """,
        ),
        Invalid(
            code="""
            from collections import namedtuple

            Point = namedtuple("Point", ["x", "y"])
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple

            Point = NamedTuple("Point", [("x", int), ("y", int)])
            """,
        ),
        Invalid(
            code="""
            from typing_extensions import NamedTuple

            Point = NamedTuple("Point", [("x", int), ("y", int)])
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple as NT

            Point = NT("Point", [("x", int), ("y", int)])
            """,
        ),
        Invalid(
            code="""
            import typing

            Point = typing.NamedTuple("Point", [("x", int), ("y", int)])
            """,
        ),
        Invalid(
            code="""
            import typing as typ

            Point = typ.NamedTuple("Point", [("x", int), ("y", int)])
            """,
        ),
        Invalid(
            code="""
            from typing import *

            Point = NamedTuple("Point", [("x", int), ("y", int)])
            """,
        ),
        Invalid(
            code="""
            from typing import *

            class Foo(NamedTuple):
                pass
            """,
        ),
        Invalid(
            code="""
            from typing_extensions import *

            class Foo(NamedTuple):
                pass
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple

            NT = NamedTuple

            class Foo(NT):
                pass
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple as NT

            class Foo(NT):
                pass

            Other = NT
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple

            A = B = NamedTuple

            class Foo(A):
                pass
            """,
        ),
    ]

    qualified_namedtuples = frozenset(
        {
            QualifiedName(name="typing.NamedTuple", source=QualifiedNameSource.IMPORT),
            QualifiedName(
                name="typing_extensions.NamedTuple",
                source=QualifiedNameSource.IMPORT,
            ),
        }
    )
    qualified_collections_namedtuple = QualifiedName(
        name="collections.namedtuple", source=QualifiedNameSource.IMPORT
    )

    def __init__(self) -> None:
        super().__init__()
        self.namedtuple_alias_nodes: set[cst.CSTNode] = set()
        self.collections_namedtuple_alias_nodes: set[cst.CSTNode] = set()
        self.star_import_modules: set[str] = set()

    def visit_Module(self, node: cst.Module) -> None:
        del node

        self.namedtuple_alias_nodes = set()
        self.collections_namedtuple_alias_nodes = set()
        self.star_import_modules = set()

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if not isinstance(node.names, cst.ImportStar):
            return

        module_name = dotted_name(node.module)
        if module_name in {"collections", "typing", "typing_extensions"}:
            self.star_import_modules.add(module_name)

    def visit_Assign(self, node: cst.Assign) -> None:
        is_namedtuple = self._is_namedtuple_expression(node.value)
        is_collections_namedtuple = self._is_collections_namedtuple_factory(node.value)
        for assign_target in node.targets:
            if not isinstance(assign_target.target, cst.Name):
                continue
            if is_namedtuple:
                self.namedtuple_alias_nodes.add(assign_target.target)
            if is_collections_namedtuple:
                self.collections_namedtuple_alias_nodes.add(assign_target.target)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if not isinstance(node.target, cst.Name) or node.value is None:
            return

        if self._is_namedtuple_expression(node.value):
            self.namedtuple_alias_nodes.add(node.target)
        if self._is_collections_namedtuple_factory(node.value):
            self.collections_namedtuple_alias_nodes.add(node.target)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        if any(self._is_namedtuple_expression(base.value) for base in node.bases):
            self.report(node, self.MESSAGE)

    def visit_Call(self, node: cst.Call) -> None:
        if self._is_collections_namedtuple_factory(node.func) or self._is_namedtuple_expression(
            node.func
        ):
            self.report(node, self.MESSAGE)

    def _is_namedtuple_expression(self, expression: cst.BaseExpression) -> bool:
        return (
            self._is_imported_namedtuple(expression)
            or self._is_namedtuple_alias(expression)
            or self._is_star_imported_namedtuple(expression)
        )

    def _is_imported_namedtuple(self, expression: cst.BaseExpression) -> bool:
        return self._has_active_qualified_import(expression, self.qualified_namedtuples)

    def _is_namedtuple_alias(self, expression: cst.BaseExpression) -> bool:
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
            and assignment_node in self.namedtuple_alias_nodes
            for assignment in reference_assignments
        )

    def _is_star_imported_namedtuple(self, expression: cst.BaseExpression) -> bool:
        if not self.star_import_modules.intersection({"typing", "typing_extensions"}):
            return False
        if not isinstance(expression, cst.Name) or expression.value != "NamedTuple":
            return False

        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        return not qualified_names

    def _is_collections_namedtuple_factory(self, expression: cst.BaseExpression) -> bool:
        if self._has_active_qualified_import(
            expression, frozenset({self.qualified_collections_namedtuple})
        ):
            return True
        if self._is_collections_namedtuple_alias(expression):
            return True
        if "collections" not in self.star_import_modules:
            return False
        if not isinstance(expression, cst.Name) or expression.value != "namedtuple":
            return False

        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        return not qualified_names

    def _is_collections_namedtuple_alias(self, expression: cst.BaseExpression) -> bool:
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
            and assignment_node in self.collections_namedtuple_alias_nodes
            for assignment in reference_assignments
        )

    def _has_active_qualified_import(
        self,
        expression: cst.BaseExpression,
        imported_names: frozenset[QualifiedName],
    ) -> bool:
        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        matching_names = imported_names.intersection(qualified_names)
        has_local_name = any(name.source is QualifiedNameSource.LOCAL for name in qualified_names)
        if matching_names and has_local_name and isinstance(expression, cst.Attribute):
            root: cst.BaseExpression = expression
            while isinstance(root, cst.Attribute):
                root = root.value
            if isinstance(root, cst.Name):
                scope = self.get_metadata(ScopeProvider, root, None)
                if scope is not None:
                    try:
                        assignments = scope[root.value]
                    except KeyError:
                        assignments = set()
                    module_names = {name.name.rpartition(".")[0] for name in matching_names}
                    reference_assignments = [
                        assignment
                        for assignment in assignments
                        if any(access.node is root for access in assignment.references)
                    ]
                    return bool(reference_assignments) and all(
                        any(
                            self._assignment_imports_module(assignment, root.value, module_name)
                            for module_name in module_names
                        )
                        for assignment in reference_assignments
                    )

        return bool(matching_names) and not has_local_name

    @staticmethod
    def _assignment_imports_module(
        assignment: object,
        bound_name: str,
        module_name: str,
    ) -> bool:
        node = getattr(assignment, "node", None)
        if not isinstance(node, cst.Import):
            return False
        for alias in node.names:
            if dotted_name(alias.name) != module_name:
                continue
            imported_name = (
                dotted_name(alias.asname.name)
                if alias.asname is not None
                else module_name.partition(".")[0]
            )
            if imported_name == bound_name:
                return True
        return False


__all__ = [
    "NoNamedTuple",
]
