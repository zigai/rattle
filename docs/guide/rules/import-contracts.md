---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-import-contracts)=

# import-contracts

<p class="rule-metadata">
  <span>Collection: <code>policy</code></span>
  <span>Autofix: No</span>
  <span>Python: Any</span>
</p>

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

## Message template

Import contract '{contract}' forbids '{source}' importing '{target}'.

Placeholder values are filled in when the violation is reported.


## Settings

```{raw} html
<table class="docutils rule-settings-table">
  <thead>
    <tr><th>Setting</th><th>Description</th><th>Type</th><th>Default</th></tr>
  </thead>
  <tbody>
<tr>
      <td><span class="rule-setting-name">contracts</span></td>
      <td>Named forbidden, layers, or independence contract tables; see the rule description.</td>
      <td><span class="rule-setting-type">list</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">[]</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">ignore_type_checking</span></td>
      <td>Ignore imports in proven TYPE_CHECKING-only branches.</td>
      <td><span class="rule-setting-type">bool</span></td>
      <td><span class="rule-setting-default rule-setting-default-constant">True</span></td>
    </tr>
<tr>
      <td><span class="rule-setting-name">source_roots</span></td>
      <td>Import search roots relative to the config root; longest matching root wins.</td>
      <td><span class="rule-setting-type">list</span></td>
      <td><span class="rule-setting-default rule-setting-default-plain">[&#x27;.&#x27;]</span></td>
    </tr>
</tbody>
</table>
```
