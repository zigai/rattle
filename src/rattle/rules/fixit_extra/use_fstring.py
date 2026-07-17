# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import re
from collections.abc import Callable

import libcst as cst
import libcst.matchers as m
from libcst.metadata import ParentNodeProvider, ScopeProvider

from rattle import Invalid, LintRule, RuleSetting, Valid

USE_FSTRING_SIMPLE_EXPRESSION_MAX_LENGTH = 30


def _match_simple_string(node: cst.BaseExpression) -> bool:
    if isinstance(node, cst.SimpleString) and "b" not in node.prefix.lower():
        # SimpleString can be a bytes and fstring don't support bytes
        # This helper is for autofixer and it only handles %s simple cases for now.
        # for the other types like %f %d, it require more processing on the format.
        # Convert a %d to fstring will change the exception type. We may get help
        # from TypeInferenceProvider to confirm the type before codedmod.
        # We leave it as future work.
        return re.fullmatch("[^%]*(%s[^%]*)+", node.raw_value) is not None
    return False


def _gen_match_simple_expression(
    codegen: Callable[[cst.CSTNode], str],
    simple_expression_max_length: int,
) -> Callable[[cst.BaseExpression], bool]:
    def _match_simple_expression(node: cst.BaseExpression) -> bool:
        # either each element in Tuple is simple expression or the entire expression is simple.
        return bool(
            (
                isinstance(node, cst.Tuple)
                and all(
                    len(codegen(elm.value)) <= simple_expression_max_length for elm in node.elements
                )
            )
            or len(codegen(node)) <= simple_expression_max_length
        )

    return _match_simple_expression


def _require_base_expression(value: object) -> cst.BaseExpression:
    if not isinstance(value, cst.BaseExpression):
        raise TypeError(f"expected a LibCST expression, got {type(value).__name__}")
    return value


class EscapeStringQuote(cst.CSTTransformer):
    def __init__(self, quote: str) -> None:
        self.quote = quote
        super().__init__()

    def _leave_simple_string(
        self,
        original_node: cst.SimpleString,
        _updated_node: cst.SimpleString,
    ) -> cst.SimpleString:
        if self.quote == original_node.quote:
            for quo in ["'", '"', "'''", '"""']:
                if quo != original_node.quote and quo not in original_node.raw_value:
                    escaped_string = cst.SimpleString(
                        original_node.prefix + quo + original_node.raw_value + quo
                    )
                    if escaped_string.evaluated_value != original_node.evaluated_value:
                        raise ValueError(
                            f"Failed to escape string:\n  original:{original_node.value}\n  escaped:{escaped_string.value}"
                        )
                    return escaped_string
            raise ValueError(
                f"Cannot find a good quote for escaping the SimpleString: {original_node.value}"
            )
        return original_node

    def leave_SimpleString(
        self,
        original_node: cst.SimpleString,
        updated_node: cst.SimpleString,
    ) -> cst.SimpleString:
        return self._leave_simple_string(original_node, updated_node)


class UseFstring(LintRule):
    """Prefer f-strings over percent formatting and ``str.format`` calls."""

    NAME = "use-f-string"
    SOURCE_PATTERNS = (".format", "%")

    MESSAGE: str = "Use an f-string instead of `%` formatting or `str.format()`."
    REFERENCES = (("PEP 498", "https://www.python.org/dev/peps/pep-0498/"),)
    SETTINGS = {
        "simple_expression_max_length": RuleSetting(
            int,
            default=USE_FSTRING_SIMPLE_EXPRESSION_MAX_LENGTH,
            description="Maximum expression length to autofix inline in an f-string.",
        ),
    }
    METADATA_DEPENDENCIES = (ParentNodeProvider, ScopeProvider)

    VALID = [
        Valid("somebody='you'; f\"Hey, {somebody}.\""),
        Valid('"hey"'),
        Valid('"hey" + "there"'),
        Valid('b"a type %s" % var'),
        Valid('u"plain unicode string"'),
    ]

    INVALID = [
        Invalid('"Hey, {somebody}.".format(somebody="you")'),
        Invalid('"%s" % "hi"', expected_replacement='''f"{'hi'!s}"'''),
        Invalid('"a name: %s" % name'),
        Invalid('u"%s" % name'),
        Invalid('"an attribute %s ." % obj.attr'),
        Invalid('r"raw string value=%s" % val'),
        Invalid('"{%s}" % val'),
        Invalid('"{%s" % val'),
        Invalid('"The type of var: %s" % type(var)'),
        Invalid(
            '"%s" % obj.this_is_a_very_long_expression(parameter)["a_very_long_key"]',
        ),
        Invalid(
            '"%s" % abcdefghijklmnopqrstuvwxyz1234567890',
            options={"simple_expression_max_length": 100},
        ),
        Invalid(
            '"type of var: %s, value of var: %s" % (type(var), var)',
            expected_replacement='f"type of var: {type(var)!s}, value of var: {var!s}"',
        ),
        Invalid("'%s\" double quote is used' % var"),
        Invalid(
            '"var1: %s, var2: %s, var3: %s, var4: %s" % (class_object.attribute, dict_lookup["some_key"], some_module.some_function(), var4)',
            expected_replacement='''f"var1: {class_object.attribute!s}, var2: {dict_lookup['some_key']!s}, var3: {some_module.some_function()!s}, var4: {var4!s}"''',
        ),
        Invalid('"a list: %s" % " ".join(var)'),
        Invalid('"%s" % (first, second)'),
    ]

    _codegen: Callable[[cst.CSTNode], str] | None

    def visit_Module(self, node: cst.Module) -> bool | None:
        self._codegen = node.code_for_node
        return super().visit_Module(node)

    def visit_Call(self, node: cst.Call) -> None:
        if m.matches(
            node,
            m.Call(func=m.Attribute(value=m.SimpleString(), attr=m.Name(value="format"))),
        ):
            self.report(node, self.MESSAGE)

    def visit_BinaryOperation(self, node: cst.BinaryOperation) -> None:
        codegen = self._codegen
        if not codegen:
            raise ValueError("No codegen found. Have we visited a Module?")
        simple_expression_max_length = self.setting("simple_expression_max_length", int)

        expr_key = "expr"
        extracts = m.extract(
            node,
            m.BinaryOperation(
                left=m.MatchIfTrue(_match_simple_string),
                operator=m.Modulo(),
                right=m.SaveMatchedNode(
                    m.MatchIfTrue(
                        _gen_match_simple_expression(codegen, simple_expression_max_length)
                    ),
                    expr_key,
                ),
            ),
        )

        if extracts:
            expr = _require_base_expression(extracts[expr_key])
            parts: list[cst.BaseFormattedStringContent] = []
            simple_string = cst.ensure_type(node.left, cst.SimpleString)
            innards = simple_string.raw_value.replace("{", "{{").replace("}", "}}")
            tokens = innards.split("%s")
            token = tokens[0]
            if len(token) > 0:
                parts.append(cst.FormattedStringText(value=token))
            expressions = (
                [elm.value for elm in expr.elements] if isinstance(expr, cst.Tuple) else [expr]
            )
            if not self._can_autofix_expressions(expr, expressions, len(tokens) - 1, codegen):
                self.report(node, self.MESSAGE)
                return
            escape_transformer = EscapeStringQuote(simple_string.quote)
            i = 1
            while i < len(tokens):
                if i - 1 >= len(expressions):
                    # Only generate warning for cases where %-string not comes with same number of elements in tuple
                    self.report(node, self.MESSAGE)
                    return
                try:
                    parts.append(
                        cst.FormattedStringExpression(
                            expression=cst.ensure_type(
                                expressions[i - 1].visit(escape_transformer),
                                cst.BaseExpression,
                            ),
                            conversion="s",
                        )
                    )
                except ValueError:
                    self.report(node, self.MESSAGE)
                    return
                token = tokens[i]
                if len(token) > 0:
                    parts.append(cst.FormattedStringText(value=token))
                i += 1
            prefix = simple_string.prefix.replace("u", "").replace("U", "")
            start = f"f{prefix}{simple_string.quote}"
            replacement = cst.FormattedString(parts=parts, start=start, end=simple_string.quote)
            self.report(node, self.MESSAGE, replacement=replacement)
        elif m.matches(
            node, m.BinaryOperation(left=m.SimpleString(), operator=m.Modulo())
        ) and isinstance(cst.ensure_type(node.left, cst.SimpleString).evaluated_value, str):
            self.report(node, self.MESSAGE)

    def _is_known_non_tuple(self, expression: cst.BaseExpression) -> bool:
        if isinstance(
            expression,
            (
                cst.BaseNumber,
                cst.Dict,
                cst.DictComp,
                cst.GeneratorExp,
                cst.Lambda,
                cst.List,
                cst.ListComp,
                cst.Set,
                cst.SetComp,
                cst.SimpleString,
            ),
        ):
            return True
        if isinstance(expression, cst.Name):
            if expression.value in {"False", "None", "True"}:
                return True
            assignments = self._reference_assignments(expression)
            return bool(assignments) and all(
                (value := self._assignment_value(assignment)) is not None
                and self._is_known_non_tuple(value)
                for assignment in assignments
            )
        if isinstance(expression, cst.Call) and isinstance(expression.func, cst.Name):
            assignments = self._reference_assignments(expression.func)
            return bool(assignments) and all(
                isinstance(getattr(assignment, "node", None), cst.ClassDef)
                for assignment in assignments
            )
        return False

    def _reference_assignments(self, name: cst.Name) -> list[object]:
        scope = self.get_metadata(ScopeProvider, name, None)
        if scope is None:
            return []
        try:
            assignments = scope[name.value]
        except KeyError:
            return []
        return [
            assignment
            for assignment in assignments
            if any(access.node is name for access in assignment.references)
        ]

    def _assignment_value(self, assignment: object) -> cst.BaseExpression | None:
        current = getattr(assignment, "node", None)
        while isinstance(current, cst.CSTNode):
            if isinstance(current, cst.Assign):
                return current.value
            if isinstance(current, cst.AnnAssign):
                return current.value
            current = self.get_metadata(ParentNodeProvider, current, None)
        return None

    def _can_autofix_expressions(
        self,
        original_expression: cst.BaseExpression,
        expressions: list[cst.BaseExpression],
        placeholder_count: int,
        codegen: Callable[[cst.CSTNode], str],
    ) -> bool:
        if (
            placeholder_count == 1
            and not isinstance(original_expression, cst.Tuple)
            and not self._is_known_non_tuple(original_expression)
        ):
            return False
        if len(expressions) != placeholder_count:
            return False
        return all(self._is_legacy_fstring_safe(value, codegen) for value in expressions)

    def _is_legacy_fstring_safe(
        self,
        expression: cst.BaseExpression,
        codegen: Callable[[cst.CSTNode], str],
    ) -> bool:
        code = codegen(expression)
        if "\\" in code or "\n" in code or "\r" in code:
            return False
        return not m.findall(expression, m.FormattedString())


__all__ = [
    "UseFstring",
]
