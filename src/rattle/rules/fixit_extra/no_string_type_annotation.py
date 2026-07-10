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
    SOURCE_PATTERNS = ("from __future__ import annotations",)

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

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            if not isinstance(alias, cst.ImportAlias):
                continue
            if m.matches(alias.name, m.Name("typing") | m.Name("typing_extensions")):
                self.typing_module_names.add(self._imported_name(alias))

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if m.matches(
            node,
            m.ImportFrom(
                module=m.Name("__future__"),
                names=[
                    m.ZeroOrMore(),
                    m.ImportAlias(name=m.Name("annotations")),
                    m.ZeroOrMore(),
                ],
            ),
        ):
            self.has_future_annotations_import = True

        if not m.matches(node.module, m.Name("typing") | m.Name("typing_extensions")):
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
        if self.in_annotation and not self.in_literal and not self._is_annotated_metadata(node):
            # This is not allowed past Python3.7 since it's no longer necessary.
            value = node.evaluated_value
            try:
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                repl = cst.parse_expression(value)
                self.report(node, self.MESSAGE, replacement=repl)
            except (UnicodeDecodeError, cst.ParserSyntaxError):
                self.report(node, self.MESSAGE)

    def _is_annotated_metadata(self, node: cst.SimpleString) -> bool:
        if not self.in_annotated:
            return False

        parent = self.get_metadata(ParentNodeProvider, node, None)
        while parent is not None and not isinstance(parent, cst.SubscriptElement):
            parent = self.get_metadata(ParentNodeProvider, parent, None)

        if not isinstance(parent, cst.SubscriptElement):
            return False

        subscript = self.get_metadata(ParentNodeProvider, parent, None)
        if subscript not in self.in_annotated or not isinstance(subscript, cst.Subscript):
            return False

        elements = list(subscript.slice)
        return parent in elements[1:]

    def _imported_name(self, alias: cst.ImportAlias) -> str:
        if alias.asname is not None:
            return alias.asname.name.value
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
