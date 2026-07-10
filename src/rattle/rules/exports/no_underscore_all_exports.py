from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import libcst as cst

from rattle import Invalid, LintRule, RuleSetting, Valid
from rattle.rules.helpers import alias_name, is_name, target_names


def _is_all_target(target: cst.BaseAssignTargetExpression) -> bool:
    return is_name(target, "__all__")


def _string_value(expression: cst.BaseExpression) -> str | None:
    if not isinstance(expression, cst.ConcatenatedString | cst.SimpleString):
        return None

    value = expression.evaluated_value
    return value if isinstance(value, str) else None


_COLLECTION_CONSTRUCTORS = {"frozenset", "list", "set", "tuple"}


@dataclass
class KnownExports:
    names: tuple[str, ...]
    kind: str


def _export_constructor_argument(node: cst.Call) -> cst.BaseExpression | None:
    if not isinstance(node.func, cst.Name):
        return None
    if node.func.value not in _COLLECTION_CONSTRUCTORS:
        return None
    if len(node.args) != 1:
        return None

    argument = node.args[0]
    return argument.value if argument.keyword is None else None


def _collection_exported_names(
    expression: cst.BaseExpression,
    known_exports: Mapping[str, KnownExports],
    shadowed_collection_constructors: set[str],
) -> list[tuple[cst.CSTNode, str]] | None:
    if isinstance(expression, cst.Name):
        known_alias = known_exports.get(expression.value)
        if known_alias is None:
            return None

        return [(expression, exported_name) for exported_name in known_alias.names]

    if isinstance(expression, cst.Call):
        return _call_exported_names(
            expression,
            known_exports,
            shadowed_collection_constructors,
        )

    if isinstance(expression, cst.BinaryOperation) and isinstance(expression.operator, cst.Add):
        return _added_exported_names(
            expression,
            known_exports,
            shadowed_collection_constructors,
        )

    if isinstance(expression, cst.List | cst.Set | cst.Tuple):
        return _literal_collection_exported_names(
            expression,
            known_exports,
            shadowed_collection_constructors,
        )

    return None


def _call_exported_names(
    expression: cst.Call,
    known_exports: Mapping[str, KnownExports],
    shadowed_collection_constructors: set[str],
) -> list[tuple[cst.CSTNode, str]] | None:
    if (
        isinstance(expression.func, cst.Name)
        and expression.func.value in shadowed_collection_constructors
    ):
        return None

    argument = _export_constructor_argument(expression)
    if argument is None:
        return None

    return _collection_exported_names(
        argument,
        known_exports,
        shadowed_collection_constructors,
    )


def _added_exported_names(
    expression: cst.BinaryOperation,
    known_exports: Mapping[str, KnownExports],
    shadowed_collection_constructors: set[str],
) -> list[tuple[cst.CSTNode, str]] | None:
    left = _collection_exported_names(
        expression.left,
        known_exports,
        shadowed_collection_constructors,
    )
    right = _collection_exported_names(
        expression.right,
        known_exports,
        shadowed_collection_constructors,
    )
    if left is None or right is None:
        return None

    return [*left, *right]


def _literal_collection_exported_names(
    expression: cst.List | cst.Set | cst.Tuple,
    known_exports: Mapping[str, KnownExports],
    shadowed_collection_constructors: set[str],
) -> list[tuple[cst.CSTNode, str]]:
    exported_names: list[tuple[cst.CSTNode, str]] = []
    for element in expression.elements:
        if isinstance(element, cst.StarredElement):
            nested_exported_names = _collection_exported_names(
                element.value,
                known_exports,
                shadowed_collection_constructors,
            )
            if nested_exported_names is not None:
                exported_names.extend(nested_exported_names)
            continue

        if (value := _string_value(element.value)) is not None:
            exported_names.append((element.value, value))

    return exported_names


def _exported_names(
    expression: cst.BaseExpression,
    known_exports: Mapping[str, KnownExports],
    shadowed_collection_constructors: set[str],
) -> list[tuple[cst.CSTNode, str]]:
    if (value := _string_value(expression)) is not None:
        return [(expression, value)]

    collection_exported_names = _collection_exported_names(
        expression,
        known_exports,
        shadowed_collection_constructors,
    )
    return collection_exported_names if collection_exported_names is not None else []


def _collection_kind(
    expression: cst.BaseExpression,
    known_exports: Mapping[str, KnownExports],
    shadowed_collection_constructors: set[str],
) -> str | None:
    kind: str | None = None
    if isinstance(expression, cst.Name):
        known = known_exports.get(expression.value)
        kind = known.kind if known is not None else None
    elif isinstance(expression, cst.List):
        kind = "list"
    elif isinstance(expression, cst.Set):
        kind = "set"
    elif isinstance(expression, cst.Tuple):
        kind = "tuple"
    elif isinstance(expression, cst.Call) and isinstance(expression.func, cst.Name):
        name = expression.func.value
        if name in _COLLECTION_CONSTRUCTORS and name not in shadowed_collection_constructors:
            kind = name
    elif isinstance(expression, cst.BinaryOperation) and isinstance(expression.operator, cst.Add):
        left_kind = _collection_kind(
            expression.left,
            known_exports,
            shadowed_collection_constructors,
        )
        right_kind = _collection_kind(
            expression.right,
            known_exports,
            shadowed_collection_constructors,
        )
        if left_kind == right_kind and left_kind in {"list", "tuple"}:
            kind = left_kind

    return kind


def _destructured_target_value_pairs(
    target: cst.List | cst.Tuple,
    value: cst.BaseExpression,
) -> list[tuple[cst.BaseAssignTargetExpression, cst.BaseExpression]] | None:
    if not isinstance(value, cst.List | cst.Tuple):
        return None
    if len(target.elements) != len(value.elements):
        return None

    pairs: list[tuple[cst.BaseAssignTargetExpression, cst.BaseExpression]] = []
    for target_element, value_element in zip(target.elements, value.elements, strict=False):
        if isinstance(target_element, cst.StarredElement | cst.StarredDictElement):
            return None
        if isinstance(value_element, cst.StarredElement | cst.StarredDictElement):
            return None
        if not isinstance(target_element.value, cst.BaseAssignTargetExpression):
            return None
        pairs.append((target_element.value, value_element.value))

    return pairs


def _all_call_export_expression(node: cst.Call) -> tuple[cst.BaseExpression, bool] | None:
    result: tuple[cst.BaseExpression, bool] | None = None
    if not isinstance(node.func, cst.Attribute) or not is_name(node.func.value, "__all__"):
        return result

    method = node.func.attr.value
    if method in {"append", "extend"} and len(node.args) == 1:
        argument = node.args[0]
        if argument.keyword is None:
            result = argument.value, method == "extend"
    elif method == "insert" and len(node.args) == 2:
        if all(argument.keyword is None for argument in node.args):
            result = node.args[1].value, False

    return result


def _alias_mutation(
    node: cst.Call,
) -> tuple[str, str, cst.BaseExpression | None] | None:
    if not isinstance(node.func, cst.Attribute):
        return None
    if not isinstance(node.func.value, cst.Name):
        return None

    alias = node.func.value.value
    method = node.func.attr.value
    if method in {"append", "extend"} and len(node.args) == 1:
        argument = node.args[0]
        expression = argument.value if argument.keyword is None else None
        return alias, method, expression
    if method == "insert" and len(node.args) == 2:
        expression = None
        if all(argument.keyword is None for argument in node.args):
            expression = node.args[1].value
        return alias, method, expression

    return alias, method, None


class NoUnderscoreAllExports(LintRule):
    """Forbid exporting underscore-prefixed names from module __all__."""

    MESSAGE = (
        "Do not export underscore-prefixed symbols in __all__. "
        "Either remove them from __all__ or rename them to be public."
    )
    SETTINGS = {
        "allowed_exports": RuleSetting(
            list[str],
            default=[],
            description="Underscore-prefixed __all__ entries to allow by exact name.",
        ),
        "allow_dunder_exports": RuleSetting(
            bool,
            default=False,
            description="Allow double-underscore names such as __version__ in __all__.",
        ),
    }

    VALID = [
        Valid('__all__ = ["PublicThing", "public_thing"]'),
        Valid('__all__: list[str] = ["public_name"]'),
        Valid("""
            def build() -> None:
                __all__ = ["_private_name"]
            """),
        Valid('module.__all__ = ["_private_name"]'),
        Valid(
            '__all__ = ["__version__"]',
            options={"allow_dunder_exports": True},
        ),
        Valid(
            '__all__ = ["_C_API", "_Sentinel"]',
            options={"allowed_exports": ["_C_API", "_Sentinel"]},
        ),
    ]

    INVALID = [
        Invalid(
            '__all__ = ["_private_name"]',
            expected_message=(
                "Do not export underscore-prefixed symbol '_private_name' in __all__. "
                "Either remove it from __all__ or rename it to be public."
            ),
        ),
        Invalid(
            """
            EXPORTS = ["_private_name"]
            __all__ = list(EXPORTS)
            """,
            expected_message=(
                "Do not export underscore-prefixed symbol '_private_name' in __all__. "
                "Either remove it from __all__ or rename it to be public."
            ),
        ),
        Invalid(
            '__all__: tuple[str, ...] = ("public_name", "_private_name")',
            expected_message=(
                "Do not export underscore-prefixed symbol '_private_name' in __all__. "
                "Either remove it from __all__ or rename it to be public."
            ),
        ),
        Invalid(
            '__all__ += ["__version__"]',
            expected_message=(
                "Do not export underscore-prefixed symbol '__version__' in __all__. "
                "Either remove it from __all__ or rename it to be public."
            ),
        ),
        Invalid(
            '__all__.append("_private_name")',
            expected_message=(
                "Do not export underscore-prefixed symbol '_private_name' in __all__. "
                "Either remove it from __all__ or rename it to be public."
            ),
        ),
        Invalid(
            '__all__.extend(["_private_name"])',
            expected_message=(
                "Do not export underscore-prefixed symbol '_private_name' in __all__. "
                "Either remove it from __all__ or rename it to be public."
            ),
        ),
        Invalid(
            '__all__.insert(0, "_private_name")',
            expected_message=(
                "Do not export underscore-prefixed symbol '_private_name' in __all__. "
                "Either remove it from __all__ or rename it to be public."
            ),
        ),
        Invalid(
            '__all__ = [*["_private_name"]]',
            expected_message=(
                "Do not export underscore-prefixed symbol '_private_name' in __all__. "
                "Either remove it from __all__ or rename it to be public."
            ),
        ),
        Invalid(
            '__all__ = ["_private" "_name"]',
            expected_message=(
                "Do not export underscore-prefixed symbol '_private_name' in __all__. "
                "Either remove it from __all__ or rename it to be public."
            ),
        ),
    ]

    def __init__(self) -> None:
        super().__init__()

        self._class_depth = 0
        self._function_depth = 0
        self._export_aliases: dict[str, KnownExports] = {}
        self._shadowed_collection_constructors: set[str] = set()

    def visit_Module(self, node: cst.Module) -> None:
        del node

        self._class_depth = 0
        self._function_depth = 0
        self._export_aliases = {}
        self._shadowed_collection_constructors = set()

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        if self._is_module_level():
            self._export_aliases.pop(node.name.value, None)
            self._remember_shadowed_collection_constructor(node.name.value)

        self._class_depth += 1

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        del original_node

        self._class_depth -= 1

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if self._is_module_level():
            self._export_aliases.pop(node.name.value, None)
            self._remember_shadowed_collection_constructor(node.name.value)

        self._function_depth += 1

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        del original_node

        self._function_depth -= 1

    def visit_Assign(self, node: cst.Assign) -> None:
        if not self._is_module_level():
            return

        if any(_is_all_target(target.target) for target in node.targets):
            self._report_exported_names(node.value)

        for target in node.targets:
            self._forget_mutated_collection_target(target.target)
        self._remember_export_aliases(node.targets, node.value)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if not self._is_module_level():
            return

        if _is_all_target(node.target):
            if node.value is not None:
                self._report_exported_names(node.value)
            return

        if node.value is None:
            self._forget_export_alias_target(node.target)
            return

        self._remember_export_alias_target(node.target, node.value)

    def visit_AugAssign(self, node: cst.AugAssign) -> None:
        if not self._is_module_level():
            return

        if isinstance(node.operator, cst.AddAssign) and _is_all_target(node.target):
            self._report_exported_names(node.value)

        if isinstance(node.target, cst.Name) and isinstance(node.operator, cst.AddAssign):
            self._remember_augmented_alias(node.target, node.value)
        else:
            self._forget_export_alias_target(node.target)

    def visit_Call(self, node: cst.Call) -> None:
        if not self._is_module_level():
            return

        all_call = _all_call_export_expression(node)
        if all_call is not None:
            expression, accepts_collection = all_call
            if accepts_collection:
                self._report_exported_names(expression)
            else:
                self._report_single_exported_name(expression)
            return

        self._remember_export_alias_mutation(node)

    def visit_Import(self, node: cst.Import) -> None:
        if not self._is_module_level():
            return

        for import_alias in node.names:
            if import_alias.asname is None:
                imported_name = import_alias.name
                while isinstance(imported_name, cst.Attribute):
                    imported_name = imported_name.value
                if not isinstance(imported_name, cst.Name):
                    continue
                bound_name = imported_name.value
            else:
                bound_name = alias_name(import_alias.asname, "")

            self._forget_bound_name(bound_name)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if not self._is_module_level():
            return

        if isinstance(node.names, cst.ImportStar):
            self._export_aliases.clear()
            if not is_name(node.module, "builtins"):
                self._shadowed_collection_constructors.update(_COLLECTION_CONSTRUCTORS)
            return

        for import_alias in node.names:
            imported_name = import_alias.name
            if not isinstance(imported_name, cst.Name):
                continue
            bound_name = alias_name(import_alias.asname, imported_name.value)
            if (
                is_name(node.module, "builtins")
                and bound_name == imported_name.value
                and bound_name in _COLLECTION_CONSTRUCTORS
            ):
                self._export_aliases.pop(bound_name, None)
                self._shadowed_collection_constructors.discard(bound_name)
            else:
                self._forget_bound_name(bound_name)

    def visit_Del(self, node: cst.Del) -> None:
        if not self._is_module_level():
            return

        for name in target_names(node.target):
            self._export_aliases.pop(name.value, None)
            self._shadowed_collection_constructors.discard(name.value)

    def _is_module_level(self) -> bool:
        return self._class_depth == 0 and self._function_depth == 0

    def _remember_export_aliases(
        self,
        targets: Sequence[cst.AssignTarget],
        value: cst.BaseExpression,
    ) -> None:
        for target in targets:
            self._remember_export_alias_target(target.target, value)

    def _remember_export_alias_target(
        self,
        target: cst.BaseAssignTargetExpression,
        value: cst.BaseExpression,
    ) -> None:
        if isinstance(target, cst.List | cst.Tuple):
            pairs = _destructured_target_value_pairs(target, value)
            if pairs is None:
                self._forget_export_alias_target(target)
                return

            for element_target, element_value in pairs:
                self._remember_export_alias_target(element_target, element_value)
            return

        if not isinstance(target, cst.Name):
            return
        if target.value == "__all__":
            return

        exported_names = _collection_exported_names(
            value,
            self._export_aliases,
            self._shadowed_collection_constructors,
        )
        if exported_names is None:
            self._export_aliases.pop(target.value, None)
        elif isinstance(value, cst.Name) and value.value in self._export_aliases:
            self._export_aliases[target.value] = self._export_aliases[value.value]
        else:
            self._export_aliases[target.value] = KnownExports(
                tuple(exported_name for _exported_node, exported_name in exported_names),
                _collection_kind(
                    value,
                    self._export_aliases,
                    self._shadowed_collection_constructors,
                )
                or "unknown",
            )

        self._remember_shadowed_collection_constructor(target.value)

    def _forget_export_alias_target(self, target: cst.BaseAssignTargetExpression) -> None:
        for name in target_names(target):
            self._export_aliases.pop(name.value, None)

    def _report_exported_names(self, expression: cst.BaseExpression) -> None:
        for exported_node, exported_name in _exported_names(
            expression,
            self._export_aliases,
            self._shadowed_collection_constructors,
        ):
            if not exported_name.startswith("_"):
                continue
            if self._is_allowed_export(exported_name):
                continue
            self.report(
                exported_node,
                (
                    f"Do not export underscore-prefixed symbol '{exported_name}' in __all__. "
                    "Either remove it from __all__ or rename it to be public."
                ),
            )

    def _report_single_exported_name(self, expression: cst.BaseExpression) -> None:
        exported_name = _string_value(expression)
        if exported_name is None or not exported_name.startswith("_"):
            return
        if self._is_allowed_export(exported_name):
            return

        self.report(
            expression,
            (
                f"Do not export underscore-prefixed symbol '{exported_name}' in __all__. "
                "Either remove it from __all__ or rename it to be public."
            ),
        )

    def _is_allowed_export(self, exported_name: str) -> bool:
        if exported_name in self.setting("allowed_exports", list[str]):
            return True

        return bool(
            self.setting("allow_dunder_exports", bool)
            and exported_name.startswith("__")
            and exported_name.endswith("__")
        )

    def _remember_export_alias_mutation(self, node: cst.Call) -> None:
        mutation = _alias_mutation(node)
        if mutation is None:
            return
        alias_name_value, method_name, expression = mutation
        known_exports = self._export_aliases.get(alias_name_value)
        if known_exports is None:
            return
        if known_exports.kind != "list":
            self._forget_known_exports(known_exports)
            return
        if expression is None:
            self._forget_known_exports(known_exports)
            return

        exported_names = self._mutation_exported_names(method_name, expression)
        if exported_names is None:
            return

        if not exported_names:
            return

        added_exports = tuple(name for _node, name in exported_names)
        if method_name == "insert":
            known_exports.names = (*added_exports, *known_exports.names)
        else:
            known_exports.names = (*known_exports.names, *added_exports)

    def _remember_augmented_alias(
        self,
        target: cst.Name,
        value: cst.BaseExpression,
    ) -> None:
        known_exports = self._export_aliases.get(target.value)
        if known_exports is None:
            return

        added_exports = _collection_exported_names(
            value,
            self._export_aliases,
            self._shadowed_collection_constructors,
        )
        if added_exports is None:
            self._forget_known_exports(known_exports)
            return

        added_names = tuple(name for _node, name in added_exports)
        if known_exports.kind == "list":
            known_exports.names = (*known_exports.names, *added_names)
        elif known_exports.kind == "tuple":
            self._export_aliases[target.value] = KnownExports(
                (*known_exports.names, *added_names),
                "tuple",
            )
        else:
            self._forget_known_exports(known_exports)

    def _mutation_exported_names(
        self,
        method_name: str,
        expression: cst.BaseExpression,
    ) -> list[tuple[cst.CSTNode, str]] | None:
        if method_name == "append":
            exported_name = _string_value(expression)
            return [] if exported_name is None else [(expression, exported_name)]

        return _collection_exported_names(
            expression,
            self._export_aliases,
            self._shadowed_collection_constructors,
        )

    def _forget_bound_name(self, name: str) -> None:
        self._export_aliases.pop(name, None)
        self._remember_shadowed_collection_constructor(name)

    def _remember_shadowed_collection_constructor(self, name: str) -> None:
        if name in _COLLECTION_CONSTRUCTORS:
            self._shadowed_collection_constructors.add(name)

    def _forget_mutated_collection_target(
        self,
        target: cst.BaseAssignTargetExpression,
    ) -> None:
        if not isinstance(target, cst.Subscript):
            return
        if not isinstance(target.value, cst.Name):
            return

        known_exports = self._export_aliases.get(target.value.value)
        if known_exports is not None:
            self._forget_known_exports(known_exports)

    def _forget_known_exports(self, known_exports: KnownExports) -> None:
        self._export_aliases = {
            name: candidate
            for name, candidate in self._export_aliases.items()
            if candidate is not known_exports
        }
