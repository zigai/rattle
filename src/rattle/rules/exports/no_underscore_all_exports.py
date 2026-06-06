from __future__ import annotations

import libcst as cst

from rattle import Invalid, LintRule, RuleSetting, Valid


def _is_all_target(target: cst.BaseAssignTargetExpression) -> bool:
    return isinstance(target, cst.Name) and target.value == "__all__"


def _exported_names(expression: cst.BaseExpression) -> list[tuple[cst.CSTNode, str]]:
    if not isinstance(expression, cst.List | cst.Set | cst.Tuple):
        return []

    exported_names: list[tuple[cst.CSTNode, str]] = []
    for element in expression.elements:
        if isinstance(element, cst.StarredElement):
            continue

        if not isinstance(element.value, cst.SimpleString):
            continue

        if not isinstance(element.value.evaluated_value, str):
            continue
        exported_names.append((element.value, element.value.evaluated_value))

    return exported_names


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
        Valid('__all__ = ("PublicThing", "public_thing")'),
        Valid(
            """
            EXPORTS = ["_private_name"]
            __all__ = list(EXPORTS)
            """
        ),
        Valid(
            """
            def build() -> None:
                __all__ = ["_private_name"]
            """
        ),
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
    ]

    def __init__(self) -> None:
        super().__init__()

        self._class_depth = 0
        self._function_depth = 0

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        del node

        self._class_depth += 1

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        del original_node

        self._class_depth -= 1

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        del node

        self._function_depth += 1

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        del original_node

        self._function_depth -= 1

    def visit_Assign(self, node: cst.Assign) -> None:
        if not self._is_module_level():
            return
        if not any(_is_all_target(target.target) for target in node.targets):
            return

        self._report_exported_names(node.value)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if not self._is_module_level():
            return
        if not _is_all_target(node.target):
            return
        if node.value is None:
            return

        self._report_exported_names(node.value)

    def visit_AugAssign(self, node: cst.AugAssign) -> None:
        if not self._is_module_level():
            return
        if not isinstance(node.operator, cst.AddAssign):
            return
        if not _is_all_target(node.target):
            return

        self._report_exported_names(node.value)

    def _is_module_level(self) -> bool:
        return self._class_depth == 0 and self._function_depth == 0

    def _report_exported_names(self, expression: cst.BaseExpression) -> None:
        for exported_node, exported_name in _exported_names(expression):
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

    def _is_allowed_export(self, exported_name: str) -> bool:
        if exported_name in self.settings["allowed_exports"]:
            return True

        return bool(
            self.settings["allow_dunder_exports"]
            and exported_name.startswith("__")
            and exported_name.endswith("__")
        )
