# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from collections.abc import Sequence

import libcst as cst
from libcst import MaybeSentinel, ensure_type, parse_expression
from libcst.metadata import (
    QualifiedName,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle import Invalid, LintRule, Valid
from rattle.rules.helpers import is_docstring_statement, normalize_import_alias

_REMOVE_IMPORT = object()


class NoNamedTuple(LintRule):
    """
    Enforce the use of ``dataclasses.dataclass`` decorator instead of ``NamedTuple`` for cleaner customization and
    inheritance. It supports default value, combining fields for inheritance, and omitting optional fields at
    instantiation. ``@dataclass`` is faster at reading an object's nested properties and executing its methods.
    """

    MESSAGE: str = "Instead of NamedTuple, consider using the @dataclass decorator from dataclasses instead for simplicity, efficiency and consistency."
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
        Valid(
            """
            @dataclass(frozen=True)
            class Foo:
                pass
            """
        ),
        Valid(
            """
            @dataclass(frozen=False)
            class Foo:
                pass
            """
        ),
        Valid(
            """
            class Foo:
                pass
            """
        ),
        Valid(
            """
            class Foo(SomeOtherBase):
                pass
            """
        ),
        Valid(
            """
            @some_other_decorator
            class Foo:
                pass
            """
        ),
        Valid(
            """
            @some_other_decorator
            class Foo(SomeOtherBase):
                pass
            """
        ),
        Valid(
            """
            from typing import NamedTuple as NT

            Other = NT
            """
        ),
    ]
    INVALID = [
        Invalid(
            code="""
            from typing import NamedTuple

            class Foo(NamedTuple):
                pass
            """,
            expected_replacement="""
            import dataclasses

            @dataclasses.dataclass(frozen=True)
            class Foo:
                pass
            """,
        ),
        Invalid(
            code="""
            from typing_extensions import NamedTuple

            class Foo(NamedTuple):
                pass
            """,
            expected_replacement="""
            import dataclasses

            @dataclasses.dataclass(frozen=True)
            class Foo:
                pass
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple as NT

            class Foo(NT):
                pass
            """,
            expected_replacement="""
            import dataclasses

            @dataclasses.dataclass(frozen=True)
            class Foo:
                pass
            """,
        ),
        Invalid(
            code="""
            import typing as typ

            class Foo(typ.NamedTuple):
                pass
            """,
            expected_replacement="""
            import dataclasses
            import typing as typ

            @dataclasses.dataclass(frozen=True)
            class Foo:
                pass
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple

            class Foo(NamedTuple, AnotherBase, YetAnotherBase):
                pass
            """,
            expected_replacement="""
            import dataclasses

            @dataclasses.dataclass(frozen=True)
            class Foo(AnotherBase, YetAnotherBase):
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
            expected_replacement="""
            import dataclasses

            class OuterClass(SomeBase):
                @dataclasses.dataclass(frozen=True)
                class InnerClass:
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
            expected_replacement="""
            import dataclasses

            @some_other_decorator
            @dataclasses.dataclass(frozen=True)
            class Foo:
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
            expected_replacement="""
            from dataclasses import dataclass

            @dataclass(frozen=True)
            class Foo:
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
            expected_replacement="""
            import dataclasses as dc

            @dc.dataclass(frozen=True)
            class Foo:
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
        self.namedtuple_classes: dict[cst.ClassDef, tuple[cst.Arg, ...]] = {}
        self.namedtuple_base_nodes: set[cst.BaseExpression] = set()
        self.namedtuple_alias_nodes: set[cst.CSTNode] = set()
        self.has_unsafe_namedtuple_reference = False
        self.has_namedtuple_star_import = False

    def visit_Module(self, node: cst.Module) -> None:
        del node

        self.namedtuple_classes = {}
        self.namedtuple_base_nodes = set()
        self.namedtuple_alias_nodes = set()
        self.has_unsafe_namedtuple_reference = False
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
        (namedtuple_base, new_bases) = self.partition_bases(node.bases)
        if namedtuple_base is not None:
            self.namedtuple_classes[node] = tuple(new_bases)
            self.namedtuple_base_nodes.add(namedtuple_base.value)

    def visit_Call(self, node: cst.Call) -> None:
        if QualifiedNameProvider.has_name(
            self,
            node.func,
            self.qualified_collections_namedtuple,
        ) or self._is_namedtuple_expression(node.func):
            self.report(node, self.MESSAGE)

    def visit_Name(self, node: cst.Name) -> None:
        if node in self.namedtuple_base_nodes:
            return
        if self._has_imported_namedtuple_name(node):
            self.has_unsafe_namedtuple_reference = True

    def leave_Module(self, original_node: cst.Module) -> None:
        if not self.namedtuple_classes:
            return
        if self.has_unsafe_namedtuple_reference:
            first_violation = next(iter(self.namedtuple_classes))
            self.report(
                first_violation,
                self.MESSAGE,
            )
            return

        decorator_expression, dataclasses_import_available = _dataclass_decorator_expression(
            original_node
        )
        decorator = cst.Decorator(decorator=decorator_expression)
        replacement = original_node.visit(
            NoNamedTupleTransformer(
                namedtuple_classes=self.namedtuple_classes,
                decorator=decorator,
                dataclasses_import_available=dataclasses_import_available,
            )
        )
        first_violation = next(iter(self.namedtuple_classes))
        self.report(
            original_node,
            self.MESSAGE,
            position_node=first_violation,
            replacement=replacement,
        )

    def partition_bases(
        self, original_bases: Sequence[cst.Arg]
    ) -> tuple[cst.Arg | None, list[cst.Arg]]:
        # Returns a tuple of NamedTuple base object if it exists, and a list of non-NamedTuple bases
        namedtuple_base: cst.Arg | None = None
        new_bases: list[cst.Arg] = []
        for base_class in original_bases:
            if self._is_namedtuple_expression(base_class.value):
                namedtuple_base = base_class
            else:
                new_bases.append(base_class)
        return (namedtuple_base, new_bases)

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

    def _has_imported_namedtuple_name(self, expression: cst.BaseExpression) -> bool:
        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        return bool(self.qualified_namedtuples.intersection(qualified_names))


def _is_future_import_statement(statement: cst.BaseStatement) -> bool:
    if not isinstance(statement, cst.SimpleStatementLine) or len(statement.body) != 1:
        return False

    import_from = statement.body[0]
    return (
        isinstance(import_from, cst.ImportFrom)
        and isinstance(import_from.module, cst.Name)
        and import_from.module.value == "__future__"
    )


def _is_dataclasses_import(statement: cst.BaseSmallStatement) -> bool:
    if isinstance(statement, cst.Import):
        return any(
            isinstance(alias.name, cst.Name) and alias.name.value == "dataclasses"
            for alias in statement.names
        )

    return (
        isinstance(statement, cst.ImportFrom)
        and isinstance(statement.module, cst.Name)
        and statement.module.value == "dataclasses"
    )


def _dataclass_decorator_from_import(statement: cst.Import) -> cst.Call | None:
    for alias in statement.names:
        if not isinstance(alias.name, cst.Name) or alias.name.value != "dataclasses":
            continue
        alias_value = "dataclasses"
        if alias.asname is not None and isinstance(alias.asname.name, cst.Name):
            alias_value = alias.asname.name.value
        return ensure_type(parse_expression(f"{alias_value}.dataclass(frozen=True)"), cst.Call)

    return None


def _dataclass_decorator_from_import_from(statement: cst.ImportFrom) -> cst.Call | None:
    if not (
        isinstance(statement.module, cst.Name)
        and statement.module.value == "dataclasses"
        and isinstance(statement.names, tuple)
    ):
        return None

    for alias in statement.names:
        if not isinstance(alias.name, cst.Name) or alias.name.value != "dataclass":
            continue
        alias_value = "dataclass"
        if alias.asname is not None and isinstance(alias.asname.name, cst.Name):
            alias_value = alias.asname.name.value
        return ensure_type(parse_expression(f"{alias_value}(frozen=True)"), cst.Call)

    return None


def _dataclass_decorator_expression(module: cst.Module) -> tuple[cst.Call, bool]:
    for statement in module.body:
        if not isinstance(statement, cst.SimpleStatementLine) or len(statement.body) != 1:
            continue

        small_statement = statement.body[0]
        if isinstance(small_statement, cst.Import):
            decorator = _dataclass_decorator_from_import(small_statement)
        elif isinstance(small_statement, cst.ImportFrom):
            decorator = _dataclass_decorator_from_import_from(small_statement)
        else:
            decorator = None

        if decorator is not None:
            return decorator, True

    return (ensure_type(parse_expression("dataclasses.dataclass(frozen=True)"), cst.Call), False)


def _rewrite_typing_import(
    statement: cst.BaseSmallStatement,
) -> cst.ImportFrom | object | None:
    if not isinstance(statement, cst.ImportFrom):
        return None
    if not (
        isinstance(statement.module, cst.Name)
        and statement.module.value in {"typing", "typing_extensions"}
    ):
        return None
    if not isinstance(statement.names, tuple):
        return None

    filtered_aliases = tuple(
        normalize_import_alias(alias)
        for alias in statement.names
        if not (isinstance(alias.name, cst.Name) and alias.name.value == "NamedTuple")
    )
    if len(filtered_aliases) == len(statement.names):
        return None
    if not filtered_aliases:
        return _REMOVE_IMPORT
    return statement.with_changes(names=filtered_aliases)


def _insert_dataclasses_import(module: cst.Module) -> cst.Module:
    dataclasses_import = cst.SimpleStatementLine(
        body=(
            cst.Import(
                names=(cst.ImportAlias(name=cst.Name("dataclasses")),),
            ),
        )
    )
    body = list(module.body)
    insert_at = 1 if body and is_docstring_statement(body[0]) else 0
    while insert_at < len(body) and _is_future_import_statement(body[insert_at]):
        insert_at += 1
    body.insert(insert_at, dataclasses_import)
    return module.with_changes(body=body)


class NoNamedTupleTransformer(cst.CSTTransformer):
    def __init__(
        self,
        *,
        namedtuple_classes: dict[cst.ClassDef, tuple[cst.Arg, ...]],
        decorator: cst.Decorator,
        dataclasses_import_available: bool,
    ) -> None:
        self.namedtuple_classes = namedtuple_classes
        self.decorator = decorator
        self.has_dataclasses_import = dataclasses_import_available

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        new_bases = self.namedtuple_classes.get(original_node)
        if new_bases is None:
            return updated_node

        return updated_node.with_changes(
            lpar=MaybeSentinel.DEFAULT,
            rpar=MaybeSentinel.DEFAULT,
            bases=list(new_bases),
            decorators=[*list(updated_node.decorators), self.decorator],
        )

    def _leave_simple_statement_line(
        self,
        _original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        if len(updated_node.body) != 1:
            return updated_node

        statement = updated_node.body[0]
        self.has_dataclasses_import = self.has_dataclasses_import or _is_dataclasses_import(
            statement
        )
        rewritten_statement = _rewrite_typing_import(statement)
        if rewritten_statement is None:
            return updated_node
        if rewritten_statement is _REMOVE_IMPORT:
            return cst.RemoveFromParent()
        return updated_node.with_changes(body=(rewritten_statement,))

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        return self._leave_simple_statement_line(original_node, updated_node)

    def _leave_module(
        self,
        _original_node: cst.Module,
        updated_node: cst.Module,
    ) -> cst.Module:
        if self.has_dataclasses_import:
            return updated_node
        return _insert_dataclasses_import(updated_node)

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        return self._leave_module(original_node, updated_node)


__all__ = [
    "NoNamedTuple",
]
