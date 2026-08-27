from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import libcst as cst
from libcst.metadata import (
    FilePathProvider,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle.rule import LintRule, RuleSetting
from rattle.rules.helpers import (
    TRANSPARENT_ANNOTATION_ARGUMENTS,
    callable_dotted_name,
    is_excluded_path,
    parse_string_expression,
    single_assignment_node,
    subscript_arguments,
)

__rattle_collect__ = False


# Every generic argument in these types describes data stored in, yielded by, or
# sent through the container. ``Any`` is therefore unsafe in every position.
_CONTAINER_NAMES = {
    "builtins.dict",
    "builtins.frozenset",
    "builtins.list",
    "builtins.set",
    "builtins.tuple",
    "collections.ChainMap",
    "collections.Counter",
    "collections.OrderedDict",
    "collections.defaultdict",
    "collections.deque",
    "collections.abc.AsyncGenerator",
    "collections.abc.AsyncIterable",
    "collections.abc.AsyncIterator",
    "collections.abc.Collection",
    "collections.abc.Container",
    "collections.abc.Generator",
    "collections.abc.ItemsView",
    "collections.abc.Iterable",
    "collections.abc.Iterator",
    "collections.abc.KeysView",
    "collections.abc.Mapping",
    "collections.abc.MappingView",
    "collections.abc.MutableMapping",
    "collections.abc.MutableSequence",
    "collections.abc.MutableSet",
    "collections.abc.Reversible",
    "collections.abc.Sequence",
    "collections.abc.Set",
    "collections.abc.ValuesView",
    "typing.AbstractSet",
    "typing.AsyncGenerator",
    "typing.AsyncIterable",
    "typing.AsyncIterator",
    "typing.ChainMap",
    "typing.Collection",
    "typing.Container",
    "typing.Counter",
    "typing.DefaultDict",
    "typing.Deque",
    "typing.Dict",
    "typing.FrozenSet",
    "typing.Generator",
    "typing.ItemsView",
    "typing.Iterable",
    "typing.Iterator",
    "typing.KeysView",
    "typing.List",
    "typing.Mapping",
    "typing.MappingView",
    "typing.MutableMapping",
    "typing.MutableSequence",
    "typing.MutableSet",
    "typing.OrderedDict",
    "typing.Reversible",
    "typing.Sequence",
    "typing.Set",
    "typing.Tuple",
    "typing.ValuesView",
}

# Only these arguments are mapping values. Counters and mapping views do not
# represent an open mapping value storage contract.
_MAPPING_VALUE_ARGUMENTS: dict[str, tuple[int, ...]] = {
    "builtins.dict": (1,),
    "collections.ChainMap": (1,),
    "collections.OrderedDict": (1,),
    "collections.defaultdict": (1,),
    "collections.abc.Mapping": (1,),
    "collections.abc.MutableMapping": (1,),
    "typing.ChainMap": (1,),
    "typing.DefaultDict": (1,),
    "typing.Dict": (1,),
    "typing.Mapping": (1,),
    "typing.MutableMapping": (1,),
    "typing.OrderedDict": (1,),
}


class _AliasCollector(cst.CSTVisitor):
    def __init__(self, rule: ContainerAnnotationRule) -> None:
        self.rule = rule

    def visit_Assign(self, node: cst.Assign) -> None:
        if len(node.targets) != 1 or not isinstance(node.targets[0].target, cst.Name):
            return
        if not isinstance(node.value, cst.Call) or (
            self.rule._qualified_name(node.value.func, node.value.func) != "typing.TypeVar"
        ):
            return
        self.rule._record_type_var((node, node.targets[0].target))

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if (
            isinstance(node.target, cst.Name)
            and node.value is not None
            and self.rule._is_type_alias_marker(node.annotation.annotation)
        ):
            self.rule._record_alias((node, node.target), node.value)
            parameter_names = self.rule._legacy_type_parameters(node.value)
            if parameter_names:
                self.rule._record_generic_alias(
                    (node, node.target),
                    parameter_names,
                    (None,) * len(parameter_names),
                    node.value,
                )

    def visit_TypeAlias(self, node: cst.TypeAlias) -> None:
        self.rule._record_alias((node, node.name), node.value)

        if node.type_parameters is None or not all(
            isinstance(parameter.param, cst.TypeVar) for parameter in node.type_parameters.params
        ):
            return
        self.rule._record_generic_alias(
            (node, node.name),
            tuple(
                parameter.param.name.value
                for parameter in node.type_parameters.params
                if isinstance(parameter.param, cst.TypeVar)
            ),
            tuple(parameter.default for parameter in node.type_parameters.params),
            node.value,
        )


class _TypeParameterSubstitution(cst.CSTTransformer):
    def __init__(self, arguments: dict[str, cst.BaseExpression]) -> None:
        self.arguments = arguments

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.BaseExpression:
        return self.arguments.get(original_node.value, updated_node)


class _TypeVariableReferenceCollector(cst.CSTVisitor):
    def __init__(self, rule: ContainerAnnotationRule) -> None:
        self.rule = rule
        self.names: list[str] = []

    def visit_Name(self, node: cst.Name) -> None:
        if self.rule._is_local_type_var_name(node) and node.value not in self.names:
            self.names.append(node.value)


class ContainerAnnotationRule(LintRule):
    """Base class for diagnostic-only rules inspecting semantic container arguments."""

    METADATA_DEPENDENCIES = (
        *LintRule.METADATA_DEPENDENCIES,
        FilePathProvider,
        QualifiedNameProvider,
        ScopeProvider,
    )
    SETTINGS = {
        "excluded_path_parts": RuleSetting(
            list[str],
            default=["tests"],
            description=(
                "Skip files whose path contains any of these components, in addition to "
                "files named test_*.py."
            ),
        ),
    }

    TARGET: str
    MAPPING_VALUES_ONLY = False

    def __init__(self) -> None:
        super().__init__()
        self._current_file_path: Path | None = None
        self._aliases: dict[cst.CSTNode, cst.BaseExpression] = {}
        self._generic_aliases: dict[
            cst.CSTNode,
            tuple[
                tuple[str, ...],
                tuple[cst.BaseExpression | None, ...],
                cst.BaseExpression,
            ],
        ] = {}
        self._type_var_nodes: set[cst.CSTNode] = set()
        self._inherently_unsafe_alias_nodes: set[cst.CSTNode] = set()

    def visit_Module(self, node: cst.Module) -> None:
        file_path = self.get_metadata(FilePathProvider, node)
        self._current_file_path = file_path if isinstance(file_path, Path) else None
        self._aliases = {}
        self._generic_aliases = {}
        self._type_var_nodes = set()
        self._inherently_unsafe_alias_nodes = set()
        node.visit(_AliasCollector(self))

    def leave_Module(self, original_node: cst.Module) -> None:
        del original_node
        self._current_file_path = None
        self._aliases = {}
        self._type_var_nodes = set()
        self._generic_aliases = {}
        self._inherently_unsafe_alias_nodes = set()

    def visit_Annotation(self, node: cst.Annotation) -> None:
        self._report_findings(node.annotation)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if (
            isinstance(node.target, cst.Name)
            and node.value is not None
            and self._is_type_alias_marker(node.annotation.annotation)
            and self._report_findings(node.value)
        ):
            self._inherently_unsafe_alias_nodes.update((node, node.target))

    def visit_TypeAlias(self, node: cst.TypeAlias) -> None:
        if self._report_findings(node.value):
            self._inherently_unsafe_alias_nodes.update((node, node.name))

    def _report_findings(self, expression: cst.BaseExpression) -> bool:
        if self._should_skip_current_file():
            return False

        findings = self._find_unsafe_containers(expression, expression, frozenset())
        for finding in findings:
            self.report(finding, self.MESSAGE)
        return bool(findings)

    def _find_unsafe_containers(  # noqa: C901, PLR0911 - recursive annotation grammar
        self,
        expression: cst.BaseExpression,
        anchor: cst.BaseExpression,
        resolving: frozenset[cst.CSTNode],
    ) -> list[cst.BaseExpression]:
        parsed = parse_string_expression(expression)
        if parsed is not None:
            return self._find_unsafe_containers(parsed, anchor, resolving)

        bare_generic_alias = self._resolve_bare_generic_alias(expression, anchor)
        if bare_generic_alias is not None:
            alias_node, specialized_value = bare_generic_alias
            if alias_node in resolving:
                return []
            return self._find_unsafe_containers(specialized_value, anchor, resolving | {alias_node})

        # The defining container is the single unsafe occurrence for a
        # non-parameterized alias; referring to it must not repeat that report.
        if self._resolve_alias(expression, anchor) is not None:
            return []

        if isinstance(expression, cst.BinaryOperation) and isinstance(
            expression.operator, cst.BitOr
        ):
            left_anchor = expression.left if anchor is expression else anchor
            right_anchor = expression.right if anchor is expression else anchor
            return [
                *self._find_unsafe_containers(expression.left, left_anchor, resolving),
                *self._find_unsafe_containers(expression.right, right_anchor, resolving),
            ]

        if not isinstance(expression, cst.Subscript):
            return []

        arguments = subscript_arguments(expression)
        if arguments is None:
            return []

        generic_alias = self._resolve_generic_alias(expression, anchor, arguments)
        if generic_alias is not None:
            alias_node, specialized_value = generic_alias
            if alias_node in resolving:
                return []
            return self._find_unsafe_containers(specialized_value, anchor, resolving | {alias_node})

        qualified_name = self._qualified_name(expression.value, anchor)
        transparent_positions = (
            TRANSPARENT_ANNOTATION_ARGUMENTS.get(qualified_name)
            if qualified_name is not None
            else None
        )
        if transparent_positions is not None or qualified_name in TRANSPARENT_ANNOTATION_ARGUMENTS:
            positions = (
                range(len(arguments)) if transparent_positions is None else transparent_positions
            )
            findings: list[cst.BaseExpression] = []
            for position in positions:
                if position < len(arguments):
                    argument = arguments[position]
                    argument_anchor = argument if anchor is expression else anchor
                    findings.extend(
                        self._find_unsafe_containers(argument, argument_anchor, resolving)
                    )
            return self._unique_nodes(findings)

        if qualified_name not in _CONTAINER_NAMES:
            return []

        unsafe_positions: Iterable[int]
        if self.MAPPING_VALUES_ONLY:
            unsafe_positions = (
                _MAPPING_VALUE_ARGUMENTS.get(qualified_name, ())
                if qualified_name is not None
                else ()
            )
        else:
            unsafe_positions = range(len(arguments))

        findings = []
        if any(
            position < len(arguments)
            and self._contains_target(arguments[position], resolving, anchor)
            for position in unsafe_positions
        ):
            findings.append(anchor)

        # Nested standard containers are independent occurrences. Arbitrary
        # domain generics are deliberately opaque and stop this traversal.
        for argument in arguments:
            argument_anchor = argument if anchor is expression else anchor
            findings.extend(self._find_unsafe_containers(argument, argument_anchor, resolving))
        return self._unique_nodes(findings)

    def _contains_target(  # noqa: PLR0911 - recursive transparent-type grammar
        self,
        expression: cst.BaseExpression,
        resolving: frozenset[cst.CSTNode],
        context: cst.CSTNode,
    ) -> bool:
        parsed = parse_string_expression(expression)
        if parsed is not None:
            return self._contains_target(parsed, resolving, context)

        alias = self._resolve_alias(expression, context)
        if alias is not None:
            alias_node, alias_value = alias
            if alias_node in resolving:
                return False
            return self._contains_target(alias_value, resolving | {alias_node}, context)

        if self._qualified_name(expression, context) == self.TARGET:
            return True

        if isinstance(expression, cst.BinaryOperation) and isinstance(
            expression.operator, cst.BitOr
        ):
            return self._contains_target(
                expression.left, resolving, context
            ) or self._contains_target(expression.right, resolving, context)

        if not isinstance(expression, cst.Subscript):
            return False
        arguments = subscript_arguments(expression)
        if arguments is None:
            return False
        qualified_name = self._qualified_name(expression.value, context)
        positions = (
            TRANSPARENT_ANNOTATION_ARGUMENTS.get(qualified_name)
            if qualified_name is not None
            else None
        )
        if positions is None and qualified_name not in TRANSPARENT_ANNOTATION_ARGUMENTS:
            return False
        selected = range(len(arguments)) if positions is None else positions
        return any(
            position < len(arguments)
            and self._contains_target(arguments[position], resolving, context)
            for position in selected
        )

    def _resolve_alias(
        self,
        expression: cst.BaseExpression,
        context: cst.CSTNode,
    ) -> tuple[cst.CSTNode, cst.BaseExpression] | None:
        if not isinstance(expression, cst.Name):
            return None
        assignment_node = single_assignment_node(self, expression, context=context)
        if assignment_node is None:
            return None
        alias_value = self._aliases.get(assignment_node)
        if alias_value is None:
            return None
        return assignment_node, alias_value

    def _resolve_generic_alias(
        self,
        expression: cst.Subscript,
        context: cst.CSTNode,
        arguments: list[cst.BaseExpression],
    ) -> tuple[cst.CSTNode, cst.BaseExpression] | None:
        if not isinstance(expression.value, cst.Name):
            return None
        return self._specialize_generic_alias(expression.value, context, arguments)

    def _resolve_bare_generic_alias(
        self,
        expression: cst.BaseExpression,
        context: cst.CSTNode,
    ) -> tuple[cst.CSTNode, cst.BaseExpression] | None:
        if not isinstance(expression, cst.Name):
            return None
        return self._specialize_generic_alias(expression, context, [])

    def _specialize_generic_alias(
        self,
        alias_name: cst.Name,
        context: cst.CSTNode,
        arguments: list[cst.BaseExpression],
    ) -> tuple[cst.CSTNode, cst.BaseExpression] | None:
        assignment_node = single_assignment_node(self, alias_name, context=context)
        if assignment_node is None or assignment_node in self._inherently_unsafe_alias_nodes:
            return None
        generic_alias = self._generic_aliases.get(assignment_node)
        if generic_alias is None:
            return None
        parameter_names, defaults, alias_value = generic_alias
        bindings = self._complete_type_bindings(parameter_names, defaults, arguments)
        if bindings is None:
            return None

        specialized_value = alias_value.visit(_TypeParameterSubstitution(bindings))
        if not isinstance(specialized_value, cst.BaseExpression):
            return None
        return assignment_node, specialized_value

    @staticmethod
    def _complete_type_bindings(
        parameter_names: tuple[str, ...],
        defaults: tuple[cst.BaseExpression | None, ...],
        arguments: list[cst.BaseExpression],
    ) -> dict[str, cst.BaseExpression] | None:
        if len(arguments) > len(parameter_names):
            return None
        bindings = dict(zip(parameter_names, arguments, strict=False))
        for position in range(len(arguments), len(parameter_names)):
            default = defaults[position]
            if default is None:
                return None
            specialized_default = default.visit(_TypeParameterSubstitution(bindings))
            if not isinstance(specialized_default, cst.BaseExpression):
                return None
            bindings[parameter_names[position]] = specialized_default
        return bindings

    def _qualified_name(  # noqa: PLR0911 - ordered metadata, scope, syntax fallback
        self, expression: cst.BaseExpression, context: cst.CSTNode
    ) -> str | None:
        qualified_names = self.get_metadata(QualifiedNameProvider, expression, set())
        if qualified_names:
            if any(name.source is QualifiedNameSource.LOCAL for name in qualified_names):
                return None
            names = {
                name.name
                for name in qualified_names
                if name.source in {QualifiedNameSource.BUILTIN, QualifiedNameSource.IMPORT}
            }
            return next(iter(names)) if len(names) == 1 else None

        dotted_name = callable_dotted_name(expression)
        if dotted_name is None:
            return None
        root, separator, suffix = dotted_name.partition(".")
        scope = self.get_metadata(ScopeProvider, context, None)
        if scope is not None:
            try:
                assignments = tuple(scope[root])
            except KeyError:
                assignments = ()
            if assignments:
                names = {
                    name.name
                    for assignment in assignments
                    for name in assignment.get_qualified_names_for(root)
                    if name.source in {QualifiedNameSource.BUILTIN, QualifiedNameSource.IMPORT}
                }
                if len(names) != 1:
                    return None
                qualified_root = next(iter(names))
                return f"{qualified_root}.{suffix}" if separator else qualified_root

        if separator:
            return None
        if root in {"dict", "frozenset", "list", "object", "set", "tuple"}:
            return f"builtins.{root}"
        return None

    def _is_type_alias_marker(self, expression: cst.BaseExpression) -> bool:
        return self._qualified_name(expression, expression) in {
            "typing.TypeAlias",
            "typing_extensions.TypeAlias",
        }

    def _record_alias(
        self,
        nodes: tuple[cst.CSTNode, ...],
        value: cst.BaseExpression,
    ) -> None:
        for node in nodes:
            self._aliases[node] = value

    def _record_generic_alias(
        self,
        nodes: tuple[cst.CSTNode, ...],
        parameter_names: tuple[str, ...],
        defaults: tuple[cst.BaseExpression | None, ...],
        value: cst.BaseExpression,
    ) -> None:
        for node in nodes:
            self._generic_aliases[node] = (parameter_names, defaults, value)

    def _record_type_var(self, nodes: tuple[cst.CSTNode, ...]) -> None:
        self._type_var_nodes.update(nodes)

    def _legacy_type_parameters(self, expression: cst.BaseExpression) -> tuple[str, ...]:
        collector = _TypeVariableReferenceCollector(self)
        expression.visit(collector)
        return tuple(collector.names)

    def _is_local_type_var_name(self, node: cst.Name) -> bool:
        scope = self.get_metadata(ScopeProvider, node, None)
        if scope is None:
            return False
        try:
            assignments = tuple(scope[node.value])
        except KeyError:
            return False
        return len(assignments) == 1 and (
            getattr(assignments[0], "node", None) in self._type_var_nodes
        )

    @staticmethod
    def _unique_nodes(nodes: list[cst.BaseExpression]) -> list[cst.BaseExpression]:
        return list(dict.fromkeys(nodes))

    def _should_skip_current_file(self) -> bool:
        if self._current_file_path is None:
            return False
        return is_excluded_path(
            self._current_file_path,
            self.setting("excluded_path_parts", list[str]),
        )
