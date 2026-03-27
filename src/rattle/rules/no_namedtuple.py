# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from collections.abc import Sequence

import libcst as cst
from libcst import MaybeSentinel, ensure_type, parse_expression
from libcst.metadata import (
    PositionProvider,
    QualifiedName,
    QualifiedNameProvider,
    QualifiedNameSource,
)

from rattle import Invalid, LintRule, Valid

_REMOVE_IMPORT = object()


class NoNamedTuple(LintRule):
    CODE = "RAT009"
    """
    Enforce the use of ``dataclasses.dataclass`` decorator instead of ``NamedTuple`` for cleaner customization and
    inheritance. It supports default value, combining fields for inheritance, and omitting optional fields at
    instantiation. See `PEP 557 <https://www.python.org/dev/peps/pep-0557>`_.
    ``@dataclass`` is faster at reading an object's nested properties and executing its methods. (`benchmark <https://medium.com/@jacktator/dataclass-vs-namedtuple-vs-object-for-performance-optimization-in-python-691e234253b9>`_).
    """

    MESSAGE: str = "Instead of NamedTuple, consider using the @dataclass decorator from dataclasses instead for simplicity, efficiency and consistency."
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)

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
    ]

    qualified_namedtuple = QualifiedName(
        name="typing.NamedTuple", source=QualifiedNameSource.IMPORT
    )

    def __init__(self) -> None:
        super().__init__()
        self.namedtuple_classes: dict[cst.ClassDef, tuple[cst.Arg, ...]] = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        (namedtuple_base, new_bases) = self.partition_bases(node.bases)
        if namedtuple_base is not None:
            self.namedtuple_classes[node] = tuple(new_bases)

    def leave_Module(self, original_node: cst.Module) -> None:
        if not self.namedtuple_classes:
            return

        decorator = cst.Decorator(
            decorator=ensure_type(
                parse_expression("dataclasses.dataclass(frozen=True)"),
                cst.Call,
            )
        )
        replacement = original_node.visit(
            _NoNamedTupleTransformer(
                namedtuple_classes=self.namedtuple_classes,
                decorator=decorator,
            )
        )
        first_violation = next(iter(self.namedtuple_classes))
        position = self.get_metadata(PositionProvider, first_violation, None)
        self.report(original_node, self.MESSAGE, position=position, replacement=replacement)

    def partition_bases(
        self, original_bases: Sequence[cst.Arg]
    ) -> tuple[cst.Arg | None, list[cst.Arg]]:
        # Returns a tuple of NamedTuple base object if it exists, and a list of non-NamedTuple bases
        namedtuple_base: cst.Arg | None = None
        new_bases: list[cst.Arg] = []
        for base_class in original_bases:
            if QualifiedNameProvider.has_name(self, base_class.value, self.qualified_namedtuple):
                namedtuple_base = base_class
            else:
                new_bases.append(base_class)
        return (namedtuple_base, new_bases)


def _is_docstring_statement(statement: cst.BaseStatement) -> bool:
    if not isinstance(statement, cst.SimpleStatementLine) or len(statement.body) != 1:
        return False

    expr = statement.body[0]
    return isinstance(expr, cst.Expr) and isinstance(expr.value, cst.SimpleString)


def _is_future_import_statement(statement: cst.BaseStatement) -> bool:
    if not isinstance(statement, cst.SimpleStatementLine) or len(statement.body) != 1:
        return False

    import_from = statement.body[0]
    return (
        isinstance(import_from, cst.ImportFrom)
        and isinstance(import_from.module, cst.Name)
        and import_from.module.value == "__future__"
    )


def _normalize_import_alias(alias: cst.ImportAlias) -> cst.ImportAlias:
    return alias.with_changes(comma=MaybeSentinel.DEFAULT)


def _is_dataclasses_import(statement: cst.BaseSmallStatement) -> bool:
    return isinstance(statement, cst.Import) and any(
        isinstance(alias.name, cst.Name)
        and alias.name.value == "dataclasses"
        and alias.asname is None
        for alias in statement.names
    )


def _rewrite_typing_import(
    statement: cst.BaseSmallStatement,
) -> cst.ImportFrom | object | None:
    if not isinstance(statement, cst.ImportFrom):
        return None
    if not isinstance(statement.module, cst.Name) or statement.module.value != "typing":
        return None
    if not isinstance(statement.names, tuple):
        return None

    filtered_aliases = tuple(
        _normalize_import_alias(alias)
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
    insert_at = 1 if body and _is_docstring_statement(body[0]) else 0
    while insert_at < len(body) and _is_future_import_statement(body[insert_at]):
        insert_at += 1
    body.insert(insert_at, dataclasses_import)
    return module.with_changes(body=body)


class _NoNamedTupleTransformer(cst.CSTTransformer):
    def __init__(
        self,
        *,
        namedtuple_classes: dict[cst.ClassDef, tuple[cst.Arg, ...]],
        decorator: cst.Decorator,
    ) -> None:
        self.namedtuple_classes = namedtuple_classes
        self.decorator = decorator
        self.has_dataclasses_import = False

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

    def leave_SimpleStatementLine(
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

    def leave_Module(self, _original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        if self.has_dataclasses_import:
            return updated_node
        return _insert_dataclasses_import(updated_node)
