# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import libcst as cst
from libcst.metadata import QualifiedName, QualifiedNameProvider, QualifiedNameSource

from rattle import CodePosition, CodeRange, Invalid, LintRule, Valid


class ExplicitFrozenDataclass(LintRule):
    """
    Requires dataclass mutability to be explicit.
    """

    MESSAGE: str = (
        "Dataclass mutability must be explicit. Add `frozen=True` for immutable "
        "value objects or `frozen=False` when instances are intentionally mutable."
    )
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)
    SOURCE_PATTERNS = ("dataclass",)
    VALID = [
        Valid(
            """
            @some_other_decorator
            class Cls: pass
            """
        ),
        Valid(
            """
            from dataclasses import dataclass
            @dataclass(frozen=False)
            class Cls: pass
            """
        ),
        Valid(
            """
            import dataclasses
            @dataclasses.dataclass(frozen=False)
            class Cls: pass
            """
        ),
        Valid(
            """
            import dataclasses as dc
            @dc.dataclass(frozen=False)
            class Cls: pass
            """
        ),
        Valid(
            """
            from dataclasses import dataclass as dc
            @dc(frozen=False)
            class Cls: pass
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            from dataclasses import dataclass
            @some_unrelated_decorator
            @dataclass  # not called as a function
            @another_unrelated_decorator
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(3, 0), end=CodePosition(3, 10)),
        ),
        Invalid(
            """
            from dataclasses import dataclass
            @dataclass()  # called as a function, no kwargs
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 12)),
        ),
        Invalid(
            """
            from dataclasses import dataclass
            @dataclass(other_kwarg=False)
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 29)),
        ),
        Invalid(
            """
            import dataclasses
            @dataclasses.dataclass
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 22)),
        ),
        Invalid(
            """
            import dataclasses
            @dataclasses.dataclass()
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 24)),
        ),
        Invalid(
            """
            import dataclasses
            @dataclasses.dataclass(other_kwarg=False)
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 41)),
        ),
        Invalid(
            """
            from dataclasses import dataclass as dc
            @dc
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 3)),
        ),
        Invalid(
            """
            from dataclasses import dataclass as dc
            @dc()
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 5)),
        ),
        Invalid(
            """
            from dataclasses import dataclass as dc
            @dc(other_kwarg=False)
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 22)),
        ),
        Invalid(
            """
            import dataclasses as dc
            @dc.dataclass
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 13)),
        ),
        Invalid(
            """
            import dataclasses as dc
            @dc.dataclass()
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 15)),
        ),
        Invalid(
            """
            import dataclasses as dc
            @dc.dataclass(other_kwarg=False)
            class Cls: pass
            """,
            range=CodeRange(start=CodePosition(2, 0), end=CodePosition(2, 32)),
        ),
    ]

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        for d in node.decorators:
            decorator = d.decorator
            if QualifiedNameProvider.has_name(
                self,
                decorator,
                QualifiedName(name="dataclasses.dataclass", source=QualifiedNameSource.IMPORT),
            ):
                if isinstance(decorator, cst.Call):
                    args = decorator.args
                else:  # decorator is either cst.Name or cst.Attribute
                    args = ()

                if not any(
                    isinstance(arg.keyword, cst.Name) and arg.keyword.value == "frozen"
                    for arg in args
                ):
                    self.report(d, self.MESSAGE)


__all__ = [
    "ExplicitFrozenDataclass",
]
