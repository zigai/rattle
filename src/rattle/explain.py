from __future__ import annotations

import ast
import inspect
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from stdl.st import colored

from rattle.console import echo
from rattle.ftypes import Invalid, Valid
from rattle.rule import LintRule, RuleReference, RuleSetting

JsonValue = None | str | int | float | bool | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True)
class SettingInfo:
    name: str
    value_type: str
    default: object | None
    required: bool
    description: str

    @classmethod
    def from_setting(cls, name: str, setting: RuleSetting) -> SettingInfo:
        default = setting.default
        required = type(default) is object
        value_type_name = getattr(setting.value_type, "__name__", None)
        return cls(
            name=name,
            value_type=str(value_type_name)
            if value_type_name is not None
            else str(setting.value_type),
            default=None if required else default,
            required=required,
            description=setting.description,
        )

    @property
    def console_default(self) -> str:
        if self.required:
            return "required"
        return str(self.default)

    def to_json_data(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "type": self.value_type,
            "default": None if self.required else _jsonable_value(self.default),
            "required": self.required,
            "description": self.description,
        }


@dataclass(frozen=True)
class ReferenceInfo:
    label: str
    url: str

    @classmethod
    def from_reference(cls, reference: RuleReference) -> ReferenceInfo:
        if isinstance(reference, str):
            return cls(label=reference, url=reference)

        label, url = reference
        return cls(label=label, url=url)

    def to_json_data(self) -> dict[str, JsonValue]:
        return {"label": self.label, "url": self.url}


@dataclass(frozen=True)
class InvalidExampleInfo:
    code: str
    replacement: str | None

    @classmethod
    def from_case(cls, case: str | Invalid) -> InvalidExampleInfo:
        if isinstance(case, Invalid):
            replacement = (
                _normalize_block_text(case.expected_replacement)
                if case.expected_replacement
                else None
            )
            return cls(code=_normalize_block_text(case.code), replacement=replacement)

        return cls(code=_normalize_block_text(case), replacement=None)

    def to_json_data(self) -> dict[str, JsonValue]:
        return {"code": self.code, "replacement": self.replacement}


@dataclass(frozen=True)
class RuleInfo:
    name: str
    status: str
    selector: str
    module: str
    description: str
    message: str
    autofix: bool
    python_version: str
    source_patterns: tuple[str, ...]
    settings: tuple[SettingInfo, ...]
    valid_examples: tuple[str, ...]
    invalid_examples: tuple[InvalidExampleInfo, ...]
    references: tuple[ReferenceInfo, ...]

    @classmethod
    def from_rule(
        cls,
        rule_type: type[LintRule],
        *,
        enabled: bool,
        example_limit: int = 2,
    ) -> RuleInfo:
        settings = tuple(
            SettingInfo.from_setting(setting_name, setting)
            for setting_name, setting in sorted(rule_type.SETTINGS.items())
        )
        message = rule_type.MESSAGE
        return cls(
            name=rule_type.name,
            status="Enabled" if enabled else "Disabled",
            selector=rule_type.qualified_name(),
            module=rule_type.__module__,
            description=_rule_documentation(rule_type),
            message=_normalize_block_text(message),
            autofix=rule_type.AUTOFIX,
            python_version=rule_type.PYTHON_VERSION or "any",
            source_patterns=tuple(
                pattern.decode("utf-8", errors="backslashreplace")
                if isinstance(pattern, bytes)
                else pattern
                for pattern in rule_type.SOURCE_PATTERNS
            ),
            settings=settings,
            valid_examples=tuple(
                _normalize_block_text(case.code if isinstance(case, Valid) else case)
                for case in rule_type.VALID[:example_limit]
            ),
            invalid_examples=tuple(
                InvalidExampleInfo.from_case(case) for case in rule_type.INVALID[:example_limit]
            ),
            references=tuple(
                ReferenceInfo.from_reference(reference) for reference in rule_type.REFERENCES
            ),
        )

    def to_json_data(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "selector": self.selector,
            "module": self.module,
            "description": self.description,
            "message": self.message,
            "autofix": self.autofix,
            "python_version": self.python_version,
            "source_patterns": list(self.source_patterns),
            "settings": [setting.to_json_data() for setting in self.settings],
            "examples": {
                "valid": list(self.valid_examples),
                "invalid": [example.to_json_data() for example in self.invalid_examples],
            },
            "references": [reference.to_json_data() for reference in self.references],
        }


def render_console_rule_info(info: RuleInfo) -> None:
    status_color = "green" if info.status == "Enabled" else "yellow"
    autofix = f" [{colored('*', color='light_cyan', style='bold')}]" if info.autofix else ""
    echo(
        f"{colored(info.name, color='light_cyan', style='bold')}{autofix}  "
        f"{colored(info.status, color=status_color, style='bold')}  "
        f"{colored(info.module, color='gray')}"
    )

    python_version = "Any" if info.python_version == "any" else info.python_version
    metadata = [f"Python: {python_version}"]
    if info.source_patterns:
        metadata.append(f"Patterns: {', '.join(info.source_patterns)}")
    echo(f"  {'  '.join(metadata)}")

    if info.description:
        echo(info.description)

    _emit_section("Message", [f"  {info.message}"] if info.message else [])
    setting_lines: list[str] = []
    for setting in info.settings:
        setting_lines.append(
            f"  {colored(setting.name, color='light_cyan', style='bold')}  "
            f"{setting.value_type}  default: {setting.console_default}"
        )
        if setting.description:
            setting_lines.append(f"    {setting.description}")
    _emit_section("Settings", setting_lines)

    _emit_section("Examples", _render_console_examples(info))
    _emit_section(
        "References",
        [f"  {reference.label}: {reference.url}" for reference in info.references],
    )


def _normalize_block_text(value: str) -> str:
    return inspect.cleandoc(value).strip()


def _rule_documentation(rule_type: type[LintRule]) -> str:
    if rule_type.__doc__:
        return _normalize_block_text(rule_type.__doc__).split("\n\n", maxsplit=1)[0]

    try:
        source = inspect.getsource(rule_type)
    except (OSError, TypeError):
        return ""

    try:
        module = ast.parse(source)
    except SyntaxError:
        return ""

    class_def = next((node for node in module.body if isinstance(node, ast.ClassDef)), None)
    if class_def is None:
        return ""

    for statement in class_def.body:
        if (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            return _normalize_block_text(statement.value.value).split("\n\n", maxsplit=1)[0]

    return ""


def _emit_section(title: str, lines: Sequence[str]) -> None:
    if not lines:
        return
    echo()
    echo(colored(title, color="light_cyan", style="bold"))
    for line in lines:
        echo(line)


def _indent_lines(value: str, prefix: str) -> list[str]:
    return [f"{prefix}{line}" for line in value.splitlines()]


def _render_console_examples(info: RuleInfo) -> list[str]:
    lines: list[str] = []
    if info.valid_examples:
        lines.append("  Valid:")
        for index, example in enumerate(info.valid_examples):
            if index:
                lines.append("")
            lines.extend(_indent_lines(example, "    "))

    if info.invalid_examples:
        if lines:
            lines.append("")
        lines.append("  Invalid:")
        for index, example in enumerate(info.invalid_examples):
            if index:
                lines.append("")
            if example.replacement and "\n" not in example.code and "\n" not in example.replacement:
                lines.append(f"    {example.code}  ->  {example.replacement}")
                continue
            lines.extend(_indent_lines(example.code, "    "))
            if example.replacement:
                lines.append("    Suggested fix:")
                lines.extend(_indent_lines(example.replacement, "      "))

    return lines


def _jsonable_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _jsonable_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_jsonable_value(item) for item in value]
    return str(value)


__all__ = [
    "RuleInfo",
    "render_console_rule_info",
]
