# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
from pathlib import Path

import libcst as cst
from libcst.metadata import (
    PositionProvider,
    QualifiedName,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle.diagnostics import FileContent
from rattle.rule import Invalid, LintRule, Valid
from rattle.rules.helpers import AssignmentAliasTracker


class UseAsyncSleepInAsyncDef(LintRule):
    """
    Do not call blocking ``time.sleep`` inside async functions; use
    ``asyncio.sleep`` or an async runtime sleep instead.
    """

    MESSAGE: str = (
        "Do not call blocking time.sleep inside async functions; use asyncio.sleep "
        "or an async runtime sleep."
    )
    METADATA_DEPENDENCIES = (QualifiedNameProvider, ScopeProvider, PositionProvider)
    VALID = [
        Valid("""
            import time
            def func():
                time.sleep(1)
            """),
        Valid("""
            from time import sleep
            def func():
                sleep(1)
            """),
        Valid("""
            from asyncio import sleep
            async def func():
                await sleep(1)
            """),
        Valid("""
            import asyncio
            async def func():
                await asyncio.sleep(1)
            """),
        Valid("""
            import time
            import asyncio
            def func():
                time.sleep(1)
            """),
        Valid("""
            import time
            import asyncio
            async def func():
                await asyncio.sleep(1)
            """),
        Valid("""
            import time
            import asyncio
            async def func():
                fut = asyncio.sleep(1)
                await fut
            """),
        Valid("""
            import something
            async def func():
                something.sleep(3)
            """),
    ]
    INVALID = [
        Invalid("""
            import time
            async def func():
                time.sleep(1)
            """),
        Invalid("""
            import time
            nap = time.sleep

            async def func():
                nap(1)
            """),
        Invalid("""
            import time
            async\tdef func():
                time.sleep(1)
            """),
        Invalid("""
            from time import sleep
            async def func():
                sleep(1)
            """),
        Invalid("""
            from time import sleep
            import asyncio
            async def func():
                sleep(2)
                asyncio.sleep(1)
            """),
        Invalid("""
            from asyncio import sleep
            import time
            async def func():
                sleep(2)
                time.sleep(1)
            """),
        Invalid("""
            import time
            async def outer():
                def inner():
                    pass
                time.sleep(1)
            """),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.function_stack: list[bool] = []
        self._time_sleep_aliases = AssignmentAliasTracker[bool](self)
        self._has_time_star_import = False

    def visit_Module(self, node: cst.Module) -> None:
        del node

        self._time_sleep_aliases.reset()
        self._has_time_star_import = False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if not isinstance(node.module, cst.Name) or node.module.value != "time":
            return

        if isinstance(node.names, cst.ImportStar):
            self._has_time_star_import = True
            return

    def visit_Assign(self, node: cst.Assign) -> None:
        for target in node.targets:
            self._time_sleep_aliases.record(target.target, node.value, self._time_sleep_alias_value)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if node.value is not None:
            self._time_sleep_aliases.record(node.target, node.value, self._time_sleep_alias_value)

    def visit_NamedExpr(self, node: cst.NamedExpr) -> None:
        self._time_sleep_aliases.record(node.target, node.value, self._time_sleep_alias_value)

    def should_lint_file(self, source: FileContent, path: Path) -> bool:
        del path
        return b"sleep" in source and b"async" in source

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self.function_stack.append(node.asynchronous is not None)

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        del original_node
        self.function_stack.pop()

    def visit_Call(self, node: cst.Call) -> None:
        if not self.function_stack or not self.function_stack[-1]:
            return

        if not self._is_time_sleep_expression(node.func):
            return

        self.report(node, self.MESSAGE)

    def _is_time_sleep_expression(self, expression: cst.BaseExpression) -> bool:
        if QualifiedNameProvider.has_name(
            self,
            expression,
            QualifiedName(name="time.sleep", source=QualifiedNameSource.IMPORT),
        ):
            return True

        if not isinstance(expression, cst.Name):
            return False

        if self._is_time_sleep_alias_name(expression):
            return True

        return (
            expression.value == "sleep"
            and self._has_time_star_import
            and self._is_unbound_name(expression)
        )

    def _is_time_sleep_alias_name(self, expression: cst.Name) -> bool:
        return self._time_sleep_aliases.resolve(expression) is True

    def _time_sleep_alias_value(self, expression: cst.BaseExpression) -> bool | None:
        if QualifiedNameProvider.has_name(
            self,
            expression,
            QualifiedName(name="time.sleep", source=QualifiedNameSource.IMPORT),
        ):
            return True
        return self._time_sleep_aliases.resolve(expression)

    def _is_unbound_name(self, expression: cst.Name) -> bool:
        scope = self.get_metadata(ScopeProvider, expression, None)
        if scope is None:
            return False

        try:
            return not scope[expression.value]
        except KeyError:
            return True


__all__ = [
    "UseAsyncSleepInAsyncDef",
]
