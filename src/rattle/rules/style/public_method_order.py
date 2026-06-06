from __future__ import annotations

from collections.abc import Sequence

import libcst as cst

from rattle import Invalid, LintRule, RuleSetting, Valid
from rattle.rules.helpers import callable_dotted_name, matches_any_pattern

_DEFAULT_CLASS_NAME_PATTERNS = ["*"]
_DEFAULT_EXCLUDED_CLASS_NAME_PATTERNS = [
    "*Enum",
    "*Model",
    "*Record",
    "*Schema",
    "*Settings",
    "*Table",
]
_ORDER_SENSITIVE_BASE_NAMES = {
    "BaseModel",
    "Enum",
    "GenericModel",
    "IntEnum",
    "Protocol",
    "SQLModel",
    "StrEnum",
    "TableBase",
    "TypedDict",
}
_ORDER_SENSITIVE_DECORATOR_NAMES = {
    "attr.define",
    "attr.frozen",
    "attrs.define",
    "attrs.frozen",
    "dataclass",
    "dataclasses.dataclass",
    "define",
    "frozen",
    "pydantic.dataclasses.dataclass",
}
_OVERLOAD_DECORATOR_NAMES = {"overload", "typing.overload", "typing_extensions.overload"}
_PUBLIC_ACCESSOR_DECORATOR_SUFFIXES = (".setter", ".deleter")
_REGISTER_DECORATOR_SUFFIXES = (".register",)


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def _base_name(base: cst.Arg) -> str | None:
    name = callable_dotted_name(base.value)
    if name is None:
        return None

    return name.rsplit(".", maxsplit=1)[-1]


def _decorator_name(decorator: cst.Decorator) -> str | None:
    return callable_dotted_name(decorator.decorator)


def _decorator_names(decorators: Sequence[cst.Decorator]) -> tuple[str, ...]:
    return tuple(
        decorator_name
        for decorator in decorators
        if (decorator_name := _decorator_name(decorator)) is not None
    )


def _is_public_accessor(method: cst.FunctionDef) -> bool:
    if method.name.value.startswith("_"):
        return False

    for decorator_name in _decorator_names(method.decorators):
        if decorator_name == "property":
            return True
        if decorator_name.endswith(_PUBLIC_ACCESSOR_DECORATOR_SUFFIXES):
            return True

    return False


def _is_order_sensitive_registration(method: cst.FunctionDef) -> bool:
    decorator_names = _decorator_names(method.decorators)

    return any(
        decorator_name == "singledispatchmethod"
        or decorator_name.endswith(_REGISTER_DECORATOR_SUFFIXES)
        for decorator_name in decorator_names
    )


def _is_overload_declaration(method: cst.FunctionDef) -> bool:
    decorator_names = _decorator_names(method.decorators)

    return any(decorator_name in _OVERLOAD_DECORATOR_NAMES for decorator_name in decorator_names)


def _has_duplicate_method_names(methods: list[cst.FunctionDef]) -> bool:
    method_names: set[str] = set()
    for method in methods:
        method_name = method.name.value
        if method_name in method_names:
            return True
        method_names.add(method_name)

    return False


def _has_order_sensitive_base(node: cst.ClassDef) -> bool:
    return any(
        base_name in _ORDER_SENSITIVE_BASE_NAMES
        for base in node.bases
        if (base_name := _base_name(base)) is not None
    )


def _has_order_sensitive_decorator(node: cst.ClassDef) -> bool:
    return any(
        decorator_name in _ORDER_SENSITIVE_DECORATOR_NAMES
        for decorator_name in _decorator_names(node.decorators)
    )


def _should_check_class(
    node: cst.ClassDef,
    class_name_patterns: list[str],
    excluded_class_name_patterns: list[str],
) -> bool:
    class_name = node.name.value
    if not matches_any_pattern(class_name_patterns, class_name):
        return False
    if matches_any_pattern(excluded_class_name_patterns, class_name):
        return False

    return not (_has_order_sensitive_base(node) or _has_order_sensitive_decorator(node))


def _ordered_methods(node: cst.ClassDef) -> list[cst.FunctionDef] | None:
    methods = [statement for statement in node.body.body if isinstance(statement, cst.FunctionDef)]
    if _has_duplicate_method_names(methods):
        return None

    return methods


def _first_order_violation(methods: list[cst.FunctionDef]) -> tuple[cst.FunctionDef, str] | None:
    first_private_helper_name: str | None = None
    for method in methods:
        method_name = method.name.value
        if _is_dunder(method_name):
            continue
        if _is_public_accessor(method):
            continue
        if _is_overload_declaration(method):
            continue
        if _is_order_sensitive_registration(method):
            continue

        if method_name.startswith("_"):
            if first_private_helper_name is None:
                first_private_helper_name = method_name

            continue

        if first_private_helper_name is not None:
            return method, first_private_helper_name

    return None


class PublicMethodOrder(LintRule):
    """Require behavior classes to define public methods before private helpers."""

    MESSAGE = "Define public methods before private helpers in behavior classes."
    SETTINGS = {
        "class_name_patterns": RuleSetting(
            list[str],
            default=_DEFAULT_CLASS_NAME_PATTERNS,
            description="Class name glob patterns to enforce. Defaults to all classes.",
        ),
        "excluded_class_name_patterns": RuleSetting(
            list[str],
            default=_DEFAULT_EXCLUDED_CLASS_NAME_PATTERNS,
            description=(
                "Class name glob patterns to skip before structural safety checks are applied."
            ),
        ),
    }

    VALID = [
        Valid(
            """
            class Workflow:
                def list_models(self) -> list[str]:
                    return []

                def _normalize(self, value: str) -> str:
                    return value
            """
        ),
        Valid(
            """
            class AiModelsService:
                def list_models(self) -> list[str]:
                    return []

                def _normalize(self, value: str) -> str:
                    return value
            """
        ),
        Valid(
            """
            from dataclasses import dataclass

            @dataclass
            class Workflow:
                value: str

                def _normalize(self) -> str:
                    return self.value

                def build(self) -> str:
                    return "ok"
            """
        ),
        Valid(
            """
            class PayloadModel(BaseModel):
                value: str

                def _normalize(self) -> str:
                    return self.value

                def build(self) -> str:
                    return "ok"
            """
        ),
        Valid(
            """
            class Workflow:
                @property
                def value(self) -> str:
                    return self._value

                def _normalize(self, value: str) -> str:
                    return value

                @value.setter
                def value(self, value: str) -> None:
                    self._value = self._normalize(value)
            """
        ),
        Valid(
            """
            from typing import overload

            class Workflow:
                @overload
                def build(self, value: str) -> str: ...

                def _normalize(self, value: str) -> str:
                    return value

                def build(self, value: str) -> str:
                    return self._normalize(value)
            """
        ),
        Valid(
            """
            from functools import singledispatchmethod

            class Workflow:
                @singledispatchmethod
                def render(self, value: object) -> str:
                    return str(value)

                def _normalize(self, value: str) -> str:
                    return value

                @render.register
                def render_str(self, value: str) -> str:
                    return self._normalize(value)
            """
        ),
        Valid(
            """
            class Workflow:
                def _normalize(self, value: str) -> str:
                    return value

                def build(self, value: str) -> str:
                    return self._normalize(value)

                def build(self, value: bytes) -> str:
                    return value.decode()
            """
        ),
        Valid(
            """
            class Helper:
                def _normalize(self, value: str) -> str:
                    return value

                def build(self) -> str:
                    return "ok"
            """,
            options={"class_name_patterns": ["*Service"]},
        ),
    ]

    INVALID = [
        Invalid(
            """
            class Workflow:
                def _normalize(self, value: str) -> str:
                    return value

                def list_models(self) -> list[str]:
                    return []
            """,
            expected_message=(
                "Define public methods before private helpers in behavior classes. "
                "Public method 'list_models' appears after private helper '_normalize'."
            ),
        ),
        Invalid(
            """
            class AiModelsService:
                def _normalize(self, value: str) -> str:
                    return value

                def list_models(self) -> list[str]:
                    return []
            """,
            expected_message=(
                "Define public methods before private helpers in behavior classes. "
                "Public method 'list_models' appears after private helper '_normalize'."
            ),
            options={"class_name_patterns": ["*Service"]},
        ),
    ]

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        if not _should_check_class(
            node,
            self.settings["class_name_patterns"],
            self.settings["excluded_class_name_patterns"],
        ):
            return

        methods = _ordered_methods(node)
        if methods is None:
            return

        violation = _first_order_violation(methods)
        if violation is None:
            return

        method, first_private_helper_name = violation
        message = (
            f"{self.MESSAGE} Public method '{method.name.value}' appears after private helper "
            f"'{first_private_helper_name}'."
        )
        self.report(method.name, message)
