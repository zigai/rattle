# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import libcst as cst
import libcst.matchers as m
from libcst.metadata import ParentNodeProvider

from rattle import CodePosition, CodeRange, Invalid, LintRule, Valid


class NoStringTypeAnnotation(LintRule):
    """Replace quoted annotations when postponed annotation evaluation is enabled."""

    MESSAGE = "Remove the quotes from this annotation; postponed evaluation is already enabled."
    REFERENCES = (("PEP 563", "https://www.python.org/dev/peps/pep-0563/#forward-references"),)
    SOURCE_PATTERNS = ("__future__",)

    VALID = [
        # Usage of a Class for instantiation and typing.
        Valid(
            """
            from a.b import Class

            def foo() -> Class:
                return Class()
            """
        ),
        Valid(
            """
            import typing
            from a.b import Class

            def foo() -> typing.Type[Class]:
                return Class
            """
        ),
        Valid(
            """
            import typing
            from a.b import Class
            from c import func

            def foo() -> typing.Optional[typing.Type[Class]]:
                return Class if func() else None
            """
        ),
        Valid(
            """
            from a.b import Class

            def foo(arg: Class) -> None:
                pass

            foo(Class())
            """
        ),
        Valid(
            """
            from a.b import Class

            module_var: Class = Class()
            """
        ),
        Valid(
            """
            from typing import Literal

            def foo() -> Literal["a", "b"]:
                return "a"
            """
        ),
        Valid(
            """
            import typing

            def foo() -> typing.Optional[typing.Literal["a", "b"]]:
                return "a"
            """
        ),
        Valid(
            """
            import typing

            def foo() -> typing.Optional[typing.Literal["class", "function"]]:
                return "class"
            """
        ),
        Valid(
            """
            from __future__ import annotations
            from typing import Annotated

            value: Annotated[int, "units"]
            """
        ),
    ]

    INVALID = [
        # Using string type hints isn't needed
        Invalid(
            """
            from __future__ import annotations

            from a.b import Class

            def foo() -> "Class":
                return Class()
            """,
            expected_replacement="""
            from __future__ import annotations

            from a.b import Class

            def foo() -> Class:
                return Class()
            """,
            range=CodeRange(start=CodePosition(5, 13), end=CodePosition(5, 20)),
        ),
        Invalid(
            """
            from __future__ import annotations

            from a.b import Class

            async def foo() -> "Class":
                return await Class()
            """,
            expected_replacement="""
            from __future__ import annotations

            from a.b import Class

            async def foo() -> Class:
                return await Class()
            """,
            range=CodeRange(start=CodePosition(5, 19), end=CodePosition(5, 26)),
        ),
        Invalid(
            """
            from __future__ import annotations

            import typing
            from a.b import Class

            def foo() -> typing.Type["Class"]:
                return Class
            """,
            expected_replacement="""
            from __future__ import annotations

            import typing
            from a.b import Class

            def foo() -> typing.Type[Class]:
                return Class
            """,
            range=CodeRange(start=CodePosition(6, 25), end=CodePosition(6, 32)),
        ),
        Invalid(
            """
            from __future__ import annotations

            import typing
            from a.b import Class
            from c import func

            def foo() -> Optional[typing.Type["Class"]]:
                return Class if func() else None
            """,
            expected_replacement="""
            from __future__ import annotations

            import typing
            from a.b import Class
            from c import func

            def foo() -> Optional[typing.Type[Class]]:
                return Class if func() else None
            """,
            range=CodeRange(start=CodePosition(7, 34), end=CodePosition(7, 41)),
        ),
        Invalid(
            """
            from __future__ import annotations

            from a.b import Class

            def foo(arg: "Class") -> None:
                pass

            foo(Class())
            """,
            expected_replacement="""
            from __future__ import annotations

            from a.b import Class

            def foo(arg: Class) -> None:
                pass

            foo(Class())
            """,
            range=CodeRange(start=CodePosition(5, 13), end=CodePosition(5, 20)),
        ),
        Invalid(
            """
            from __future__ import annotations

            from a.b import Class

            module_var: "Class" = Class()
            """,
            expected_replacement="""
            from __future__ import annotations

            from a.b import Class

            module_var: Class = Class()
            """,
            range=CodeRange(start=CodePosition(5, 12), end=CodePosition(5, 19)),
        ),
        Invalid(
            """
            from __future__ import annotations

            import typing
            from typing_extensions import Literal
            from a.b import Class

            def foo() -> typing.Tuple[Literal["a", "b"], "Class"]:
                return Class()
            """,
            expected_replacement="""
            from __future__ import annotations

            import typing
            from typing_extensions import Literal
            from a.b import Class

            def foo() -> typing.Tuple[Literal["a", "b"], Class]:
                return Class()
            """,
            range=CodeRange(start=CodePosition(7, 45), end=CodePosition(7, 52)),
        ),
        Invalid(
            """
            from __future__ import annotations

            value: b"\\xff"
            """,
        ),
    ]

    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.in_annotation: set[cst.Annotation] = set()
        self.in_literal: set[cst.Subscript] = set()
        self.in_annotated: set[cst.Subscript] = set()
        self.has_future_annotations_import = False
        self.typing_module_names: set[str] = set()
        self.literal_names: set[str] = set()
        self.annotated_names: set[str] = set()

    def visit_Module(self, node: cst.Module) -> None:
        for statement in node.body:
            if not isinstance(statement, cst.SimpleStatementLine):
                continue
            for small_statement in statement.body:
                if isinstance(small_statement, cst.Import):
                    self._record_import(small_statement)
                elif isinstance(small_statement, cst.ImportFrom):
                    self._record_import_from(small_statement)

    def visit_Import(self, node: cst.Import) -> None:
        self._record_import(node)

    def _record_import(self, node: cst.Import) -> None:
        for alias in node.names:
            if not isinstance(alias, cst.ImportAlias):
                continue
            if m.matches(alias.name, m.Name("typing") | m.Name("typing_extensions")):
                self.typing_module_names.add(self._imported_name(alias))

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        self._record_import_from(node)

    def _record_import_from(self, node: cst.ImportFrom) -> None:
        if (
            isinstance(node.module, cst.Name)
            and node.module.value == "__future__"
            and not isinstance(node.names, cst.ImportStar)
            and any(
                isinstance(alias.name, cst.Name) and alias.name.value == "annotations"
                for alias in node.names
            )
        ):
            self.has_future_annotations_import = True

        if node.module is None or not m.matches(
            node.module,
            m.Name("typing") | m.Name("typing_extensions"),
        ):
            return
        if isinstance(node.names, cst.ImportStar):
            self.literal_names.add("Literal")
            self.annotated_names.add("Annotated")
            return

        for alias in node.names:
            if not isinstance(alias, cst.ImportAlias):
                continue
            if m.matches(alias.name, m.Name("Literal")):
                self.literal_names.add(self._imported_name(alias))
            if m.matches(alias.name, m.Name("Annotated")):
                self.annotated_names.add(self._imported_name(alias))

    def visit_Annotation(self, node: cst.Annotation) -> None:
        self.in_annotation.add(node)

    def leave_Annotation(self, original_node: cst.Annotation) -> None:
        self.in_annotation.remove(original_node)

    def visit_Subscript(self, node: cst.Subscript) -> None:
        if not self.has_future_annotations_import:
            return
        if self.in_annotation and self._is_typing_subscript(node, self.literal_names, "Literal"):
            self.in_literal.add(node)
        if self.in_annotation and self._is_typing_subscript(
            node, self.annotated_names, "Annotated"
        ):
            self.in_annotated.add(node)

    def leave_Subscript(self, original_node: cst.Subscript) -> None:
        if not self.has_future_annotations_import:
            return
        if original_node in self.in_literal:
            self.in_literal.remove(original_node)
        if original_node in self.in_annotated:
            self.in_annotated.remove(original_node)

    def visit_SimpleString(self, node: cst.SimpleString) -> None:
        if not self.has_future_annotations_import:
            return
        parent = self.get_metadata(ParentNodeProvider, node, None)
        if isinstance(parent, cst.ConcatenatedString):
            return
        if self.in_annotation and not self.in_literal and not self._is_annotated_metadata(node):
            self._report_string(node, node.evaluated_value)

    def visit_ConcatenatedString(self, node: cst.ConcatenatedString) -> None:
        if not self.has_future_annotations_import:
            return
        if self.in_annotation and not self.in_literal and not self._is_annotated_metadata(node):
            self._report_string(node, node.evaluated_value)

    def _report_string(self, node: cst.BaseString, value: str | bytes | None) -> None:
        if value is None:
            self.report(node, self.MESSAGE)
            return
        try:
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            repl = cst.parse_expression(value)
            self.report(node, self.MESSAGE, replacement=repl)
        except (UnicodeDecodeError, cst.ParserSyntaxError):
            self.report(node, self.MESSAGE)

    def _is_annotated_metadata(self, node: cst.BaseString) -> bool:
        if not self.in_annotated:
            return False

        current: cst.CSTNode = node
        while (parent := self.get_metadata(ParentNodeProvider, current, None)) is not None:
            if isinstance(parent, cst.SubscriptElement):
                subscript = self.get_metadata(ParentNodeProvider, parent, None)
                if subscript in self.in_annotated and isinstance(subscript, cst.Subscript):
                    return parent in list(subscript.slice)[1:]
            current = parent
        return False

    def _imported_name(self, alias: cst.ImportAlias) -> str:
        if alias.asname is not None:
            alias_name = alias.asname.name
            if isinstance(alias_name, cst.Name):
                return alias_name.value
            return cst.Module([]).code_for_node(alias_name)
        if isinstance(alias.name, cst.Name):
            return alias.name.value
        return cst.Module([]).code_for_node(alias.name).split(".", 1)[0]

    def _is_typing_subscript(
        self,
        node: cst.Subscript,
        direct_names: set[str],
        attr_name: str,
    ) -> bool:
        value = node.value
        if isinstance(value, cst.Name):
            return value.value in direct_names
        if isinstance(value, cst.Attribute) and isinstance(value.attr, cst.Name):
            return (
                value.attr.value == attr_name
                and isinstance(value.value, cst.Name)
                and value.value.value in self.typing_module_names
            )
        return False


__all__ = [
    "NoStringTypeAnnotation",
]
