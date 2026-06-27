# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import libcst as cst
import libcst.matchers as m
from libcst.metadata import ParentNodeProvider

from rattle import Invalid, LintRule, Valid
from rattle.rules.helpers import callable_dotted_name, normalize_import_alias

# The ABCs that have been moved to `collections.abc`
ABCS = frozenset(
    {
        "AsyncGenerator",
        "AsyncIterable",
        "AsyncIterator",
        "Awaitable",
        "Buffer",
        "ByteString",
        "Callable",
        "Collection",
        "Container",
        "Coroutine",
        "Generator",
        "Hashable",
        "ItemsView",
        "Iterable",
        "Iterator",
        "KeysView",
        "Mapping",
        "MappingView",
        "MutableMapping",
        "MutableSequence",
        "MutableSet",
        "Reversible",
        "Sequence",
        "Set",
        "Sized",
        "ValuesView",
    }
)


def _is_import_error_expression(expression: cst.BaseExpression) -> bool:
    name = callable_dotted_name(expression)
    if name is None:
        return False

    return name.rsplit(".", 1)[-1] == "ImportError"


class DeprecatedABCImport(LintRule):
    """Require collection ABCs to be imported from collections.abc."""

    NAME = "use-collections-abc"

    MESSAGE = "ABCs must be imported from collections.abc"
    PYTHON_VERSION = ">= 3.3"
    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    VALID = [
        Valid("from collections.abc import Container"),
        Valid("from collections.abc import Container, Hashable"),
        Valid("from collections.abc import (Container, Hashable)"),
        Valid("from collections import defaultdict"),
        Valid("from collections import abc"),
        Valid("import collections"),
        Valid("import collections.abc"),
        Valid("import collections.abc.Container"),
        Valid("""
            class MyTest(collections.Something):
                def test(self):
                    pass
            """),
        Valid("""
            try:
                from collections.abc import Mapping
            except ImportError:
                from collections import Mapping
            """),
        Valid("""
            try:
                from collections.abc import Mapping, Container
            except ImportError:
                from collections import Mapping, Container
            """),
        Valid("""
            try:
                from collections.abc import Mapping, Container
            except ImportError:
                def fallback_import():
                    from collections import Mapping, Container
            """),
        Valid("""
            try:
                from collections.abc import Mapping, Container
            except Exception:
                exit()
            """),
        Valid("""
            try:
                from collections import defaultdict
            except Exception:
                exit()
            """),
    ]
    INVALID = [
        Invalid(
            "from collections import Container",
            expected_replacement="from collections.abc import Container",
        ),
        Invalid(
            "from collections import Container, Hashable",
            expected_replacement="from collections.abc import Container, Hashable",
        ),
        Invalid(
            "from collections import (Container, Hashable)",
            expected_replacement="from collections.abc import (Container, Hashable)",
        ),
        Invalid(
            "import collections.Container",
            expected_replacement="import collections.abc.Container",
        ),
        Invalid(
            "import collections.Container as cont",
            expected_replacement="import collections.abc.Container as cont",
        ),
        Invalid(
            "from collections import defaultdict, Container",
            expected_replacement="from collections import defaultdict\nfrom collections.abc import Container",
        ),
        Invalid(
            "from collections import defaultdict\nfrom collections import Container",
            expected_replacement="from collections import defaultdict\nfrom collections.abc import Container",
        ),
        Invalid(
            "from collections import defaultdict, Container\nfrom collections import OrderedDict, Mapping",
            expected_replacement=(
                "from collections import defaultdict\n"
                "from collections.abc import Container\n"
                "from collections import OrderedDict\n"
                "from collections.abc import Mapping"
            ),
        ),
        Invalid(
            """
            class MyTest(collections.Container):
                def test(self):
                    pass
            """,
            expected_replacement="""
            class MyTest(collections.abc.Container):
                def test(self):
                    pass
            """,
        ),
        Invalid(
            """
            try:
                work()
            except ValueError:
                from collections import Mapping
            """,
            expected_replacement="""
            try:
                work()
            except ValueError:
                from collections.abc import Mapping
            """,
        ),
    ]

    def __init__(self) -> None:
        super().__init__()

    def is_import_error_except_block(self, node: cst.CSTNode) -> bool:
        """
        Check if the node is in an ImportError except block.

        Imports from ``collections`` are allowed there because they may be fallback
        imports for older runtimes after a failed ``collections.abc`` import.
        """
        parent = self.get_metadata(ParentNodeProvider, node, None)
        while parent is not None and not isinstance(parent, cst.Module):
            if isinstance(parent, cst.ExceptHandler):
                return self._handles_import_error(parent)

            parent = self.get_metadata(ParentNodeProvider, parent, None)

        return False

    def _handles_import_error(self, node: cst.ExceptHandler) -> bool:
        if node.type is None:
            return False
        if _is_import_error_expression(node.type):
            return True
        if not isinstance(node.type, cst.Tuple):
            return False

        return any(_is_import_error_expression(element.value) for element in node.type.elements)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        """This catches the `from collections import <ABC>` cases."""
        if self.is_import_error_except_block(node):
            return

        # Get imports in this statement
        import_names = [name.name.value for name in node.names] if type(node.names) is tuple else []
        # Filter the imports for ABC imports
        import_names_in_abc = [name in ABCS for name in import_names]
        if node.module and node.module.value == "collections" and any(import_names_in_abc):
            # Replacing the case where there are ABCs mixed with non-ABCs requires
            # splitting a single import statement into two separate imports. This
            # is handled by replacing the parent statement with two statements.
            if not all(import_names_in_abc):
                parent = self.get_metadata(ParentNodeProvider, node, None)
                if not isinstance(parent, cst.SimpleStatementLine):
                    self.report(node, self.MESSAGE)
                    return

                assert isinstance(node.names, tuple)
                non_abcs = tuple(
                    normalize_import_alias(alias)
                    for alias in node.names
                    if alias.name.value not in ABCS
                )
                abcs = tuple(
                    normalize_import_alias(alias)
                    for alias in node.names
                    if alias.name.value in ABCS
                )
                replacement = cst.FlattenSentinel(
                    [
                        cst.SimpleStatementLine(
                            body=(
                                cst.ImportFrom(
                                    module=cst.Name(value="collections"),
                                    names=non_abcs,
                                ),
                            )
                        ),
                        cst.SimpleStatementLine(
                            body=(
                                cst.ImportFrom(
                                    module=cst.Attribute(
                                        value=cst.Name(value="collections"),
                                        attr=cst.Name(value="abc"),
                                    ),
                                    names=abcs,
                                ),
                            )
                        ),
                    ]
                )
                self.report(parent, self.MESSAGE, replacement=replacement)
            else:
                self.report(
                    node,
                    self.MESSAGE,
                    replacement=node.with_changes(
                        module=cst.Attribute(
                            value=cst.Name(value="collections"),
                            attr=cst.Name(value="abc"),
                        )
                    ),
                )

    def visit_ImportAlias(self, node: cst.ImportAlias) -> None:
        """This catches the `import collections.<ABC>` cases."""
        if m.matches(
            node,
            m.ImportAlias(
                name=m.Attribute(
                    value=m.Name("collections"),
                    attr=m.OneOf(*[m.Name(abc) for abc in ABCS]),
                )
            ),
        ):
            self.report(
                node,
                self.MESSAGE,
                replacement=node.with_changes(
                    name=cst.Attribute(
                        value=cst.Attribute(
                            value=cst.Name(value="collections"),
                            attr=cst.Name(value="abc"),
                        ),
                        attr=cst.ensure_type(node.name, cst.Attribute).attr,
                    )
                ),
            )

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        # Iterate over inherited Classes and search for `collections.<ABC>`
        for base in node.bases:
            if m.matches(
                base,
                m.Arg(
                    value=m.Attribute(
                        value=m.Name("collections"),
                        attr=m.OneOf(*[m.Name(abc) for abc in ABCS]),
                    )
                ),
            ):
                # Report + replace `collections.<ABC>` with `collections.abc.<ABC>`
                # while keeping the remaining classes.
                self.report(
                    node,
                    self.MESSAGE,
                    replacement=node.with_changes(
                        bases=[
                            (
                                cst.Arg(
                                    value=cst.Attribute(
                                        value=cst.Attribute(
                                            value=cst.Name("collections"),
                                            attr=cst.Name("abc"),
                                        ),
                                        attr=base.value.attr,
                                    ),
                                )
                                if m.matches(
                                    base,
                                    m.Arg(
                                        value=m.Attribute(
                                            value=m.Name("collections"),
                                            attr=m.OneOf(*[m.Name(abc) for abc in ABCS]),
                                        )
                                    ),
                                )
                                and isinstance(base.value, cst.Attribute)
                                else base
                            )
                            for base in node.bases
                        ]
                    ),
                )


__all__ = [
    "DeprecatedABCImport",
]
