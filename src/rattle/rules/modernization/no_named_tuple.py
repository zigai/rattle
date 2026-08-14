# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
from libcst.metadata import (
    PositionProvider,
    QualifiedName,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle.rule import Invalid, LintRule, Valid
from rattle.rules.helpers import (
    AssignmentAliasTracker,
    attribute_root_is_imported_module,
    dotted_name,
)


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
    METADATA_DEPENDENCIES = (QualifiedNameProvider, ScopeProvider, PositionProvider)
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
        self._aliases = AssignmentAliasTracker[str](self)
        self.star_import_modules: set[str] = set()

    def visit_Module(self, node: cst.Module) -> None:
        del node

        self._aliases.reset()
        self.star_import_modules = set()

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if not isinstance(node.names, cst.ImportStar):
            return

        module_name = dotted_name(node.module)
        if module_name in {"collections", "typing", "typing_extensions"}:
            self.star_import_modules.add(module_name)

    def visit_Assign(self, node: cst.Assign) -> None:
        for assign_target in node.targets:
            self._aliases.record(assign_target.target, node.value, self._alias_value)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if node.value is None:
            return
        self._aliases.record(node.target, node.value, self._alias_value)

    def visit_NamedExpr(self, node: cst.NamedExpr) -> None:
        self._aliases.record(node.target, node.value, self._alias_value)

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
        return self._aliases.resolve(expression) == "typing"

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
        return self._aliases.resolve(expression) == "collections"

    def _alias_value(self, expression: cst.BaseExpression) -> str | None:
        if self._is_imported_namedtuple(expression):
            return "typing"
        if self._has_active_qualified_import(
            expression, frozenset({self.qualified_collections_namedtuple})
        ):
            return "collections"
        return self._aliases.resolve(expression)

    def _has_active_qualified_import(
        self,
        expression: cst.BaseExpression,
        imported_names: frozenset[QualifiedName],
    ) -> bool:
        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        matching_names = imported_names.intersection(qualified_names)
        has_local_name = any(name.source is QualifiedNameSource.LOCAL for name in qualified_names)
        if matching_names and has_local_name and isinstance(expression, cst.Attribute):
            module_names = {name.name.rpartition(".")[0] for name in matching_names}
            return attribute_root_is_imported_module(self, expression, module_names)

        return bool(matching_names) and not has_local_name


__all__ = [
    "NoNamedTuple",
]
