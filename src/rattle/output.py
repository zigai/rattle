from __future__ import annotations

import re
import sys
from pathlib import Path

from libcst import ParserSyntaxError
from stdl.st import colored

from rattle.ast import AstParseError
from rattle.console import color_precomputed_diff
from rattle.ftypes import CodePosition, CodeRange, FileContent, LintViolation, OutputFormat, Result

_PARSER_ERROR_PREFIX = re.compile(r"^parser error:\s*", re.IGNORECASE)
_PARSER_LOCATION_PREFIX = re.compile(r"^error at \d+:\d+:\s*", re.IGNORECASE)


def render_rattle_result(
    result: Result,
    *,
    path: Path,
    color: bool = False,
    brief: bool = False,
    brief_rule_width: int | None = None,
) -> str | None:
    """Render a result using the default terminal presentation."""
    if result.violation:
        return _render_violation(
            path,
            result.violation,
            result.source,
            color=color,
            brief=brief,
            brief_rule_width=brief_rule_width,
        )

    if result.error:
        error, _ = result.error
        if isinstance(error, ParserSyntaxError):
            return _render_syntax_error(path, error, result.source, color=color, brief=brief)
        if isinstance(error, AstParseError):
            return _render_ast_parse_error(path, error, result.source, color=color, brief=brief)

    return None


def render_console_result(
    result: Result,
    *,
    path: Path,
    show_diff: bool = False,
    output_format: OutputFormat = OutputFormat.rattle,
    output_template: str = "",
    brief: bool = False,
    brief_rule_width: int | None = None,
) -> str | None:
    if result.violation:
        return _render_console_violation(
            result,
            path=path,
            show_diff=show_diff,
            output_format=output_format,
            output_template=output_template,
            brief=brief,
            brief_rule_width=brief_rule_width,
        )

    if result.error:
        return _render_console_error(
            result,
            path=path,
            output_format=output_format,
            brief=brief,
        )

    return None


def _render_console_violation(
    result: Result,
    *,
    path: Path,
    show_diff: bool,
    output_format: OutputFormat,
    output_template: str,
    brief: bool,
    brief_rule_width: int | None,
) -> str:
    violation = result.violation
    assert violation is not None
    assert violation.range is not None

    if output_format == OutputFormat.rattle:
        rendered = render_rattle_result(
            result,
            path=path,
            color=True,
            brief=brief,
            brief_rule_width=brief_rule_width,
        )
        if rendered is None:
            raise NotImplementedError("missing rattle renderer for lint violation")
        lines = [rendered]
        if show_diff and violation.diff:
            lines.append(color_precomputed_diff(violation.diff).rstrip("\n"))
        if not brief or (show_diff and violation.diff):
            lines.append("")
        return "\n".join(lines)

    rule_name = violation.rule_name
    start_line = violation.range.start.line
    start_col = violation.range.start.column
    message = violation.message
    if violation.autofixable:
        message += " (has autofix)"

    if output_format == OutputFormat.vscode:
        rendered = f"{path}:{start_line}:{start_col} {rule_name}: {message}"
    elif output_format == OutputFormat.custom:
        rendered = output_template.format(
            message=message,
            path=path,
            result=result,
            rule_name=rule_name,
            start_col=start_col,
            start_line=start_line,
        )
    else:
        raise NotImplementedError(f"output-format = {output_format!r}")

    rendered = colored(rendered, color="yellow")
    if show_diff and violation.diff:
        rendered += "\n" + color_precomputed_diff(violation.diff).rstrip("\n")
    return rendered


def _render_console_error(
    result: Result,
    *,
    path: Path,
    output_format: OutputFormat,
    brief: bool,
) -> str:
    error, tb = result.error or (None, "")
    assert error is not None

    if output_format == OutputFormat.rattle and isinstance(
        error, (AstParseError, ParserSyntaxError)
    ):
        rendered = render_rattle_result(result, path=path, color=True, brief=brief)
        if rendered is None:
            raise NotImplementedError("missing rattle renderer for syntax error")
        return rendered + ("\n" if not brief else "")

    rendered = colored(f"{path}: EXCEPTION: {error}", color="red")
    return f"{rendered}\n{tb.strip()}" if tb else rendered


def _render_violation(
    path: Path,
    violation: LintViolation,
    source: FileContent | None,
    *,
    color: bool,
    brief: bool,
    brief_rule_width: int | None = None,
) -> str:
    assert violation.range is not None
    rule_name = violation.rule_name
    if brief and brief_rule_width is not None:
        rule_name = f"{rule_name:<{brief_rule_width}}"
    header = _error_style(rule_name, color=color)
    if violation.autofixable:
        header += f" {_fix_marker(color=color)}"
    header += f" {violation.message}"
    if brief:
        return _render_brief_block(
            header=header, path=path, code_range=violation.range, color=color
        )

    lines = _render_block(
        header=header,
        path=path,
        code_range=violation.range,
        source=source,
        help_message=("Apply the available autofix" if violation.autofixable else None),
        color=color,
    )
    return "\n".join(lines)


def _render_syntax_error(
    path: Path,
    error: ParserSyntaxError,
    source: FileContent | None,
    *,
    color: bool,
    brief: bool,
) -> str:
    source_lines = _decode_source_lines(source)
    line_text = source_lines[error.raw_line - 1] if error.raw_line - 1 < len(source_lines) else ""
    end_column = _find_syntax_error_end_column(line_text, error.raw_column)
    error_range = CodeRange(
        start=CodePosition(line=error.raw_line, column=error.raw_column),
        end=CodePosition(line=error.raw_line, column=end_column),
    )
    header = (
        f"{_error_style('invalid-syntax', color=color)}: {_normalize_parser_message(error.message)}"
    )
    if brief:
        return _render_brief_block(header=header, path=path, code_range=error_range, color=color)

    lines = _render_block(
        header=header,
        path=path,
        code_range=error_range,
        source=source,
        color=color,
    )
    return "\n".join(lines)


def _render_ast_parse_error(
    path: Path,
    error: AstParseError,
    source: FileContent | None,
    *,
    color: bool,
    brief: bool,
) -> str:
    source_lines = _decode_source_lines(source)
    line_text = source_lines[error.line - 1] if error.line - 1 < len(source_lines) else ""

    if error.end_line is not None and error.end_column is not None:
        end_line = error.end_line
        end_column = error.end_column
    else:
        end_line = error.line
        end_column = _find_syntax_error_end_column(line_text, error.column)

    if end_line < error.line or (end_line == error.line and end_column <= error.column):
        end_line = error.line
        end_column = _find_syntax_error_end_column(line_text, error.column)

    error_range = CodeRange(
        start=CodePosition(line=error.line, column=error.column),
        end=CodePosition(line=end_line, column=end_column),
    )
    header = f"{_error_style('ast-parse-error', color=color)}: {error}"
    if brief:
        return _render_brief_block(header=header, path=path, code_range=error_range, color=color)

    lines = _render_block(
        header=header,
        path=path,
        code_range=error_range,
        source=source,
        color=color,
    )
    return "\n".join(lines)


def _render_brief_block(*, header: str, path: Path, code_range: CodeRange, color: bool) -> str:
    display_column = code_range.start.column + 1
    return (
        f"{header} "
        f"{_line_no_style(' --> ', color=color)}"
        f"{path.as_posix()}:{code_range.start.line}:{display_column}"
    )


def _render_block(
    *,
    header: str,
    path: Path,
    code_range: CodeRange,
    source: FileContent | None,
    help_message: str | None = None,
    color: bool,
) -> list[str]:
    source_lines = _decode_source_lines(source)
    display_column = code_range.start.column + 1
    lines = [
        header,
        (
            f"{_line_no_style(' --> ', color=color)}"
            f"{path.as_posix()}:{code_range.start.line}:{display_column}"
        ),
    ]

    if not source_lines:
        if help_message:
            lines.extend(
                [
                    _line_no_style("  |", color=color),
                    f"{_help_style('help', color=color)}: {help_message}",
                ]
            )
        return lines

    first_context_line = max(1, code_range.start.line - 1)
    last_context_line = min(len(source_lines), code_range.end.line + 1)
    gutter_width = len(str(last_context_line))
    blank_gutter = _line_no_style(f"{' ' * gutter_width} |", color=color)

    lines.append(blank_gutter)
    for line_number in range(first_context_line, last_context_line + 1):
        source_line = source_lines[line_number - 1]
        rendered_source = source_line.expandtabs()
        lines.append(
            f"{_line_no_style(f'{line_number:>{gutter_width}} |', color=color)} {rendered_source}"
        )
        if code_range.start.line <= line_number <= code_range.end.line:
            underline = _render_underline(
                source_line=source_line,
                line_number=line_number,
                code_range=code_range,
                color=color,
            )
            lines.append(f"{blank_gutter} {underline}")

    lines.append(blank_gutter)
    if help_message:
        lines.append(f"{_help_style('help', color=color)}: {help_message}")

    return lines


def _render_underline(
    *, source_line: str, line_number: int, code_range: CodeRange, color: bool
) -> str:
    displayed_line = source_line.expandtabs()

    if code_range.start.line == code_range.end.line:
        start_display = _to_display_column(source_line, code_range.start.column)
        end_display = _to_display_column(source_line, code_range.end.column)
        width = max(1, end_display - start_display)
        return f"{' ' * start_display}{_secondary_code_style('^' * width, color=color)}"

    if line_number == code_range.start.line:
        start_display = _to_display_column(source_line, code_range.start.column)
        width = max(1, len(displayed_line) - start_display)
        return f"{' ' * start_display}{_secondary_code_style('^' * width, color=color)}"

    if line_number == code_range.end.line:
        end_display = _to_display_column(source_line, code_range.end.column)
        width = max(1, end_display)
        return _secondary_code_style("^" * width, color=color)

    width = max(1, len(displayed_line))
    return _secondary_code_style("^" * width, color=color)


def _decode_source_lines(source: FileContent | None) -> list[str]:
    if source is None:
        return []

    return source.decode("utf-8", errors="replace").splitlines()


def _normalize_parser_message(message: str) -> str:
    normalized = _PARSER_ERROR_PREFIX.sub("", message.strip())
    return _PARSER_LOCATION_PREFIX.sub("", normalized)


def _find_syntax_error_end_column(line_text: str, start_column: int) -> int:
    if start_column >= len(line_text):
        return start_column + 1

    if match := re.match(r"[A-Za-z0-9_]+", line_text[start_column:]):
        return start_column + len(match.group(0))

    return start_column + 1


def _to_display_column(source_line: str, column: int) -> int:
    return len(source_line[:column].expandtabs())


def _error_style(text: str, *, color: bool) -> str:
    return colored(text, color="light_red", style="bold") if color else text


def _help_style(text: str, *, color: bool) -> str:
    return colored(text, color="light_cyan", style="bold") if color else text


def _line_no_style(text: str, *, color: bool) -> str:
    fg = "light_cyan" if sys.platform == "win32" else "light_blue"
    return colored(text, color=fg, style="bold") if color else text


def _secondary_code_style(text: str, *, color: bool) -> str:
    return colored(text, color="red", style="bold") if color else text


def _fix_marker(*, color: bool) -> str:
    return f"[{_help_style('*', color=color)}]"


__all__ = ["render_console_result", "render_rattle_result"]
