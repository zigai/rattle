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
        self.has_namedtuple_star_import = False

    def visit_Module(self, node: cst.Module) -> None:
        del node

        self.namedtuple_alias_nodes = set()
        self.has_namedtuple_star_import = False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if (
            isinstance(node.module, cst.Name)
            and node.module.value in {"typing", "typing_extensions"}
            and isinstance(node.names, cst.ImportStar)
        ):
            self.has_namedtuple_star_import = True

    def visit_Assign(self, node: cst.Assign) -> None:
        if self._is_namedtuple_expression(node.value):
            for assign_target in node.targets:
                if isinstance(assign_target.target, cst.Name):
                    self.namedtuple_alias_nodes.add(assign_target.target)
        else:
            for assign_target in node.targets:
                if isinstance(assign_target.target, cst.Name):
                    self.namedtuple_alias_nodes.discard(assign_target.target)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        if any(self._is_namedtuple_expression(base.value) for base in node.bases):
            self.report(node, self.MESSAGE)

    def visit_Call(self, node: cst.Call) -> None:
        if QualifiedNameProvider.has_name(
            self,
            node.func,
            self.qualified_collections_namedtuple,
        ) or self._is_namedtuple_expression(node.func):
            self.report(node, self.MESSAGE)

    def _is_namedtuple_expression(self, expression: cst.BaseExpression) -> bool:
        return (
            self._is_imported_namedtuple(expression)
            or self._is_namedtuple_alias(expression)
            or self._is_star_imported_namedtuple(expression)
        )

    def _is_imported_namedtuple(self, expression: cst.BaseExpression) -> bool:
        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        if any(
            qualified_name.source is QualifiedNameSource.LOCAL for qualified_name in qualified_names
        ):
            return False

        return bool(self.qualified_namedtuples.intersection(qualified_names))

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

        return bool(assignments) and all(
            (assignment_node := getattr(assignment, "node", None)) is not None
            and assignment_node in self.namedtuple_alias_nodes
            for assignment in assignments
        )

    def _is_star_imported_namedtuple(self, expression: cst.BaseExpression) -> bool:
        if not self.has_namedtuple_star_import:
            return False
        if not isinstance(expression, cst.Name) or expression.value != "NamedTuple":
            return False

        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        return not qualified_names


__all__ = [
    "NoNamedTuple",
]
