from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import cache
from pathlib import Path

import libcst as cst
from libcst.metadata import (
    FilePathProvider,
    ParentNodeProvider,
    QualifiedNameProvider,
    QualifiedNameSource,
)
from msgspec import Struct, convert, field

from rattle.rule import LintRule, RuleConfigurationError, RuleSetting
from rattle.rules.helpers import dotted_name


class _Forbidden(Struct, tag="forbidden", tag_field="type", forbid_unknown_fields=True):
    name: str
    source: list[str]
    forbid: list[str]
    allow: list[str] = field(default_factory=list)
    message: str = ""


class _Layer(Struct, forbid_unknown_fields=True):
    modules: list[str]
    exclude: list[str] = field(default_factory=list)


class _Layers(Struct, tag="layers", tag_field="type", forbid_unknown_fields=True):
    name: str
    layers: list[_Layer]
    root: str = ""
    message: str = ""


class _Independence(Struct, tag="independence", tag_field="type", forbid_unknown_fields=True):
    name: str
    packages: list[str]
    public: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    message: str = ""


_Contract = _Forbidden | _Layers | _Independence
_ContractOptions = list[dict[str, str | list[str] | list[dict[str, list[str]]]]]


def _validate_patterns(patterns: Sequence[str], *, required: bool = False) -> None:
    if required and not patterns:
        raise ValueError("expected at least one module pattern")
    for pattern in patterns:
        if any(part not in {"*", "**"} and not part.isidentifier() for part in pattern.split(".")):
            raise ValueError(f"invalid module pattern: {pattern!r}")


def _parse_contracts(value: object) -> list[_Contract]:
    contracts = convert(value, type=list[_Contract], strict=True)
    names: set[str] = set()
    for contract in contracts:
        if not contract.name.strip() or contract.name in names:
            raise ValueError("contract names must be nonempty and unique")
        names.add(contract.name)
        if isinstance(contract, _Forbidden):
            _validate_patterns(contract.source, required=True)
            _validate_patterns(contract.forbid, required=True)
            _validate_patterns(contract.allow)
        elif isinstance(contract, _Layers):
            if contract.root and any(not part.isidentifier() for part in contract.root.split(".")):
                raise ValueError("layer root must be a literal module name")
            if len(contract.layers) < 2:
                raise ValueError("expected at least two layers, high to low")
            for layer in contract.layers:
                _validate_patterns(layer.modules, required=True)
                _validate_patterns(layer.exclude)
        else:
            _validate_patterns(contract.packages, required=True)
            _validate_patterns(contract.public)
            _validate_patterns(contract.exclude)
            parents = {pattern.rpartition(".")[0] for pattern in contract.packages}
            if len(parents) != 1 or any("**" in pattern for pattern in contract.packages):
                raise ValueError("independent packages must be siblings without '**'")
    return contracts


def _matches(pattern: str, module: str) -> bool:
    pattern_parts = pattern.split(".")
    module_parts = module.split(".") if module else []

    @cache
    def match(pattern_index: int, module_index: int) -> bool:
        if pattern_index == len(pattern_parts):
            return module_index == len(module_parts)
        part = pattern_parts[pattern_index]
        if part == "**":
            return match(pattern_index + 1, module_index) or (
                module_index < len(module_parts) and match(pattern_index, module_index + 1)
            )
        return (
            module_index < len(module_parts)
            and (part == "*" or part == module_parts[module_index])
            and match(pattern_index + 1, module_index + 1)
        )

    return match(0, 0)


def _matches_any(patterns: Sequence[str], module: str) -> bool:
    return any(_matches(pattern, module) for pattern in patterns)


def _prefixes(module: str) -> list[str]:
    parts = module.split(".")
    return [".".join(parts[:index]) for index in range(1, len(parts) + 1)]


def _layer_index(contract: _Layers, module: str) -> int | None:
    if contract.root:
        if not module.startswith(f"{contract.root}."):
            return None
        module = module[len(contract.root) + 1 :]
    for index, layer in enumerate(contract.layers):
        if _matches_any(layer.modules, module) and not _matches_any(layer.exclude, module):
            return index
    return None


def _sibling(contract: _Independence, module: str) -> str | None:
    if _matches_any(contract.exclude, module):
        return None
    for pattern in contract.packages:
        prefix = ".".join(module.split(".")[: len(pattern.split("."))])
        if _matches(pattern, prefix):
            return prefix
    return None


def _breaks_contract(contract: _Contract, source: str, target: str) -> bool:
    if isinstance(contract, _Forbidden):
        return (
            _matches_any(contract.source, source)
            and not _matches_any(contract.allow, source)
            and any(_matches_any(contract.forbid, prefix) for prefix in _prefixes(target))
        )
    if isinstance(contract, _Layers):
        source_layer = _layer_index(contract, source)
        target_layer = None
        for prefix in reversed(_prefixes(target)):
            target_layer = _layer_index(contract, prefix)
            if target_layer is not None:
                break
        return source_layer is not None and target_layer is not None and source_layer > target_layer
    source_package = _sibling(contract, source)
    target_package = _sibling(contract, target)
    if source_package is None or target_package is None or source_package == target_package:
        return False
    public_path = target[len(target_package) + 1 :]
    return not any(_matches_any(contract.public, prefix) for prefix in _prefixes(public_path))


class ImportContracts(LintRule):
    """
    Enforce named module boundaries, ordered layers, and public sibling APIs.

    Checks direct imports only, including function-local imports. It does not
    follow re-exports or dependency chains, import target packages, or inspect
    their export lists. Keep third-party bans on every layer below the layer
    allowed to use them: for example, forbid ``fastapi`` and ``starlette`` in
    domains, integrations, platform, and models, not just domains. A layers
    contract then makes imports of higher-layer wrappers direct violations.
    This is not transitive dependency analysis; same-layer wrappers and
    re-exports still require their own boundaries.

    ``source_roots`` are paths relative to Rattle's configuration root, like
    Python's import search paths. Use ``["src"]`` for ``src/package/`` layouts,
    or ``[".", "apps/server/src"]`` for a monorepo with root-level scripts.
    The longest matching root wins. Package initializer files are not required,
    so namespace packages work. Initializer files name their package, not a
    separate initializer submodule. Files outside these roots are not checked.
    ``enable-root-import`` only controls loading rules; it does not set these
    source roots.

    Patterns use dotted segments: ``*`` matches exactly one segment and ``**``
    matches zero or more. Source patterns, source exceptions, layer modules,
    and exclusions match the whole module name. Use ``package.**`` to include
    a package and its descendants. Forbidden targets are package boundaries:
    ``webkit`` also forbids ``webkit.responses``. Public sibling submodules
    likewise include their descendants. Aliases do not change import targets.
    ``from x import y`` checks ``x.y`` even when ``y`` might be a submodule;
    star imports check ``x`` itself. Relative imports resolve from the source
    module's package, including inside package initializers.

    Configure ``contracts`` as an array of tables, each with a unique ``name``,
    a ``type``, and an optional ``message``. Every breached contract is reported
    once per imported alias (or star), with its name and message.

    * ``forbidden``: ``source`` and ``forbid`` are nonempty pattern lists.
      Optional ``allow`` patterns exempt **source modules**, not import targets.
      For example, use ``source = ["parcel.**"]``, ``forbid = ["webkit"]``,
      and ``allow = ["parcel.*.router", "parcel.*.dependencies"]``.
    * ``layers``: ``layers`` lists tables from high to low. Each has ``modules``
      patterns and optional ``exclude`` patterns. Patterns are relative to the
      optional literal ``root`` module; omit it for fully qualified patterns.
      The first matching layer wins. Import targets also match module prefixes,
      so importing a member of an exact layer module still counts.
      Modules in one layer are peers and can import each other; lower layers
      cannot import higher ones. Exclude
      infrastructure packages from wildcard domain layers. For example:
      ``layers = [{modules = ["edge.**"]}, {modules = ["core.**"]}]`` with
      ``root = "parcel"``. Modules outside all layers are not constrained.
    * ``independence``: ``packages`` selects sibling package boundaries,
      such as ``["parcel.*"]``. It accepts ``*`` but not ``**``. Optional
      ``exclude`` patterns remove infrastructure modules. ``public`` lists
      submodules relative to each sibling, such as ``["service", "schemas",
      "dependencies"]``. Imports within a sibling are unrestricted; imports
      of another sibling's package root or internals are forbidden. An empty
      ``public`` list forbids all cross-sibling imports.

    For a backend with HTTP, Temporal, CLI, and scripts entrypoints, put those
    modules in one peer layer, followed by domains, integrations, platform,
    and models. Exclude those infrastructure packages from the domain wildcard.
    Keep models lowest so ``platform.db`` can import them. Use separate
    forbidden contracts for cross-entrypoint restrictions.

    A minimal configuration for a ``src/`` layout is:

    ```toml
    [tool.rattle]
    root = true
    enable = ["import-contracts"]

    [tool.rattle.options.import-contracts]
    source_roots = ["src"]

    [[tool.rattle.options.import-contracts.contracts]]
    type = "forbidden"
    name = "transport-purity"
    source = ["parcel.**"]
    forbid = ["webkit"]
    allow = ["parcel.*.router", "parcel.*.dependencies"]
    message = "Keep transport at the edge."
    ```

    By default, imports in proven ``typing.TYPE_CHECKING`` or
    ``typing_extensions.TYPE_CHECKING`` branches are ignored, including import
    aliases and nested bodies. Runtime branches and shadowed local names still
    count. Set ``ignore_type_checking = false`` to check type-only imports too.
    """

    MESSAGE = "Import contract '{contract}' forbids '{source}' importing '{target}'."
    METADATA_DEPENDENCIES = (FilePathProvider, ParentNodeProvider, QualifiedNameProvider)
    SETTINGS = {
        "source_roots": RuleSetting(
            list[str],
            default=["."],
            description="Import search roots relative to the config root; longest matching root wins.",
        ),
        "contracts": RuleSetting(
            _ContractOptions,
            default=[],
            description="Named forbidden, layers, or independence contract tables; see the rule description.",
        ),
        "ignore_type_checking": RuleSetting(
            bool,
            default=True,
            description="Ignore imports in proven TYPE_CHECKING-only branches.",
        ),
    }

    def __init__(self) -> None:
        super().__init__()
        self._contracts: list[_Contract] = []
        self._module_name: str | None = None
        self._package_name: str | None = None

    def configure(self, raw_settings: Mapping[str, object]) -> None:
        super().configure(raw_settings)
        roots = self.setting("source_roots", list[str])
        if not roots or any(Path(root).is_absolute() or ".." in Path(root).parts for root in roots):
            raise RuleConfigurationError(
                f"{self.name}: source_roots must be nonempty paths within the config root"
            )
        try:
            self._contracts = _parse_contracts(self.settings["contracts"])
        except ValueError as e:
            raise RuleConfigurationError(f"{self.name}: {e}") from None

    def should_lint_file(self, source: bytes, _path: Path) -> bool:
        return bool(self._contracts) and b"import" in source

    def visit_Module(self, node: cst.Module) -> None:
        self._module_name = None
        self._package_name = None
        path = self.get_metadata(FilePathProvider, node, None)
        assert path is not None
        roots = sorted(
            (self._config_root / root for root in self.setting("source_roots", list[str])),
            key=lambda root: len(root.parts),
            reverse=True,
        )
        for root in roots:
            if not path.is_relative_to(root.resolve()):
                continue
            parts = list(path.relative_to(root.resolve()).with_suffix("").parts)
            is_package = parts[-1] == "__init__"
            if is_package:
                parts.pop()
            if parts and all(part.isidentifier() for part in parts):
                self._module_name = ".".join(parts)
                self._package_name = ".".join(parts if is_package else parts[:-1])
            return

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            target = dotted_name(alias.name)
            assert target is not None
            self._check(alias, target)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        module = dotted_name(node.module) if node.module is not None else ""
        assert module is not None
        if node.relative:
            package = self._package_name.split(".") if self._package_name else []
            level = len(node.relative)
            if level > len(package):
                return
            base = ".".join(package[: len(package) - level + 1])
            module = f"{base}.{module}" if module else base
        if isinstance(node.names, cst.ImportStar):
            self._check(node.names, module)
        else:
            for alias in node.names:
                member = dotted_name(alias.name)
                assert member is not None
                self._check(alias, f"{module}.{member}" if module else member)

    def _check(self, node: cst.CSTNode, target: str) -> None:
        if self._module_name is None or (
            self.setting("ignore_type_checking", bool) and self._is_type_only(node)
        ):
            return
        for contract in self._contracts:
            if _breaks_contract(contract, self._module_name, target):
                message = self.MESSAGE.format(
                    contract=contract.name, source=self._module_name, target=target
                )
                if contract.message:
                    message = f"{message} {contract.message}"
                self.report(node, message)

    def _is_type_only(self, node: cst.CSTNode) -> bool:
        parent = self.get_metadata(ParentNodeProvider, node, None)
        while parent is not None:
            if isinstance(parent, cst.If):
                truth = self._runtime_truth(parent.test)
                if (truth is False and node is parent.body) or (
                    truth is True and node is parent.orelse
                ):
                    return True
            node = parent
            parent = self.get_metadata(ParentNodeProvider, node, None)
        return False

    def _runtime_truth(self, node: cst.BaseExpression) -> bool | None:
        names = self.get_metadata(QualifiedNameProvider, node, set())
        if names and all(
            name.source is QualifiedNameSource.IMPORT
            and name.name in {"typing.TYPE_CHECKING", "typing_extensions.TYPE_CHECKING"}
            for name in names
        ):
            return False
        if isinstance(node, cst.UnaryOperation) and isinstance(node.operator, cst.Not):
            truth = self._runtime_truth(node.expression)
            return None if truth is None else not truth
        if isinstance(node, cst.BooleanOperation):
            left = self._runtime_truth(node.left)
            right = self._runtime_truth(node.right)
            decisive = not isinstance(node.operator, cst.And)
            if left is decisive or right is decisive:
                return decisive
            return left if left is right else None
        return None
