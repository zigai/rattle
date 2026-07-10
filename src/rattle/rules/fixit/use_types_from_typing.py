# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import libcst
from libcst.metadata import QualifiedNameProvider, ScopeProvider

from rattle import Invalid, LintRule, Valid

REPLACE_BUILTIN_TYPE_ANNOTATION: str = (
    "Python 3.8 does not support `{builtin_type}[...]` annotations; "
    "use `typing.{correct_type}` instead."
)

BUILTINS_TO_REPLACE: set[str] = {"dict", "list", "set", "tuple"}
QUALIFIED_BUILTINS_TO_REPLACE: set[str] = {f"builtins.{s}" for s in BUILTINS_TO_REPLACE}


class UseTypesFromTyping(LintRule):
    """
    For Python ``< 3.9`` only, require ``typing.Dict``, ``typing.List``,
    ``typing.Set``, and ``typing.Tuple`` annotations instead of builtin generic
    aliases such as ``dict[str, str]``.
    """

    MESSAGE = REPLACE_BUILTIN_TYPE_ANNOTATION
    PYTHON_VERSION = "< 3.9"

    METADATA_DEPENDENCIES = (
        QualifiedNameProvider,
        ScopeProvider,
    )
    VALID = [
        Valid(
            """
            def function(list: List[str]) -> None:
                pass
            """
        ),
        Valid(
            """
            def function() -> None:
                thing: Dict[str, str] = {}
            """
        ),
        Valid(
            """
            def function() -> None:
                thing: Tuple[str]
            """
        ),
        Valid(
            """
            from typing import Dict, List
            def function() -> bool:
                    return Dict == List
            """
        ),
        Valid(
            """
            from typing import List as list
            from graphene import List

            def function(a: list[int]) -> List[int]:
                    return []
            """
        ),
        Valid(
            """
            from builtins import list as ListType

            LT = ListType

            class LT:
                def __class_getitem__(cls, item):
                    return cls

            def func(value: LT[str]) -> None:
                pass
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            from typing import List
            def whatever(list: list[str]) -> None:
                pass
            """,
            expected_replacement="""
            from typing import List
            def whatever(list: List[str]) -> None:
                pass
            """,
        ),
        Invalid(
            """
            def function(list: list[str]) -> None:
                pass
            """,
        ),
        Invalid(
            """
            def func() -> None:
                thing: dict[str, str] = {}
            """,
        ),
        Invalid(
            """
            def func() -> None:
                thing: tuple[str]
            """,
        ),
        Invalid(
            """
            from typing import Dict
            def func() -> None:
                thing: dict[str, str] = {}
            """,
            expected_replacement="""
            from typing import Dict
            def func() -> None:
                thing: Dict[str, str] = {}
            """,
        ),
        Invalid(
            """
            from builtins import list as ListType

            def func(value: ListType[str]) -> None:
                pass
            """,
        ),
        Invalid(
            """
            from builtins import list as ListType

            LT = ListType

            def func(value: LT[str]) -> None:
                pass
            """,
        ),
        Invalid(
            """
            from builtins import list as ListType

            LT = OtherLT = ListType

            def func(value: OtherLT[str]) -> None:
                pass
            """,
        ),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.annotation_counter: int = 0
        self.builtin_type_aliases_by_node: dict[libcst.CSTNode, str] = {}

    def visit_Module(self, node: libcst.Module) -> None:
        del node

        self.annotation_counter = 0
        self.builtin_type_aliases_by_node = {}

    def visit_Assign(self, node: libcst.Assign) -> None:
        if not isinstance(node.value, libcst.Name):
            return

        builtin_type = self._builtin_type_name(node.value)
        for assign_target in node.targets:
            target = assign_target.target
            if not isinstance(target, libcst.Name):
                continue
            if builtin_type is None:
                self.builtin_type_aliases_by_node.pop(target, None)
            else:
                self.builtin_type_aliases_by_node[target] = builtin_type

    def visit_AnnAssign(self, node: libcst.AnnAssign) -> None:
        if not isinstance(node.target, libcst.Name) or node.value is None:
            return

        builtin_type = self._builtin_type_name(node.value)
        if builtin_type is not None:
            self.builtin_type_aliases_by_node[node.target] = builtin_type

    def visit_Annotation(self, node: libcst.Annotation) -> None:
        del node
        self.annotation_counter += 1

    def leave_Annotation(self, original_node: libcst.Annotation) -> None:
        del original_node
        self.annotation_counter -= 1

    def visit_Subscript(self, node: libcst.Subscript) -> None:
        if self.annotation_counter <= 0:
            return

        builtin_type = self._builtin_type_name(node.value)
        if builtin_type is None:
            return

        correct_type = builtin_type.title()
        replacement = (
            libcst.Name(correct_type)
            if self._typing_type_is_unambiguously_available(node.value, correct_type)
            else None
        )
        self.report(
            node.value,
            REPLACE_BUILTIN_TYPE_ANNOTATION.format(
                builtin_type=builtin_type, correct_type=correct_type
            ),
            replacement=replacement,
        )

    def _builtin_type_name(self, node: libcst.BaseExpression) -> str | None:
        qualified_names = self.get_metadata(QualifiedNameProvider, node, set())
        if not qualified_names:
            if isinstance(node, libcst.Name) and node.value in BUILTINS_TO_REPLACE:
                return node.value
            return None

        if isinstance(node, libcst.Name):
            alias_builtin_type = self._alias_builtin_type_name(node)
            if alias_builtin_type is not None:
                return alias_builtin_type

        if any(
            qualified_name.name not in QUALIFIED_BUILTINS_TO_REPLACE
            for qualified_name in qualified_names
        ):
            return None

        first_name = next(iter(qualified_names)).name
        return first_name.rsplit(".", 1)[-1]

    def _alias_builtin_type_name(self, node: libcst.Name) -> str | None:
        scope = self.get_metadata(ScopeProvider, node, None)
        if scope is None:
            return None

        try:
            assignments = scope[node.value]
        except KeyError:
            return None

        reference_assignments = [
            assignment
            for assignment in assignments
            if any(access.node is node for access in assignment.references)
        ]
        alias_types = [
            self.builtin_type_aliases_by_node.get(assignment_node)
            if (assignment_node := getattr(assignment, "node", None)) is not None
            else None
            for assignment in reference_assignments
        ]
        if not alias_types or any(alias_type is None for alias_type in alias_types):
            return None

        unique_alias_types = {alias_type for alias_type in alias_types if alias_type is not None}
        if len(unique_alias_types) != 1:
            return None

        return unique_alias_types.pop()

    def _typing_type_is_unambiguously_available(
        self,
        node: libcst.BaseExpression,
        correct_type: str,
    ) -> bool:
        scope = self.get_metadata(ScopeProvider, node, None)
        if scope is None:
            return False
        try:
            assignments = scope[correct_type]
        except KeyError:
            return False

        return bool(assignments) and all(
            self._assignment_imports_typing_type(assignment, correct_type)
            for assignment in assignments
        )

    @staticmethod
    def _assignment_imports_typing_type(assignment: object, type_name: str) -> bool:
        node = getattr(assignment, "node", None)
        if not isinstance(node, libcst.ImportFrom):
            return False
        if not isinstance(node.module, libcst.Name) or node.module.value != "typing":
            return False
        if isinstance(node.names, libcst.ImportStar):
            return False

        for alias in node.names:
            if not isinstance(alias.name, libcst.Name) or alias.name.value != type_name:
                continue
            bound_name = type_name
            if alias.asname is not None and isinstance(alias.asname.name, libcst.Name):
                bound_name = alias.asname.name.value
            if bound_name == type_name:
                return True
        return False


__all__ = [
    "UseTypesFromTyping",
]
