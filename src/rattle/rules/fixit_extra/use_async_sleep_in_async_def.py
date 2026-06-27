# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
from pathlib import Path

import libcst as cst
from libcst.metadata import (
    QualifiedName,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from rattle import FileContent, Invalid, LintRule, Valid


class UseAsyncSleepInAsyncDef(LintRule):
    """
    Do not call blocking ``time.sleep`` inside async functions; use
    ``asyncio.sleep`` or an async runtime sleep instead.
    """

    MESSAGE: str = (
        "Do not call blocking time.sleep inside async functions; use asyncio.sleep "
        "or an async runtime sleep."
    )
    METADATA_DEPENDENCIES = (QualifiedNameProvider, ScopeProvider)
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
        self._time_sleep_alias_nodes: set[cst.CSTNode] = set()
        self._has_time_star_import = False

    def visit_Module(self, node: cst.Module) -> None:
        del node

        self._time_sleep_alias_nodes = set()
        self._has_time_star_import = False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if not isinstance(node.module, cst.Name) or node.module.value != "time":
            return

        if isinstance(node.names, cst.ImportStar):
            self._has_time_star_import = True
            return

        for alias in node.names:
            if not isinstance(alias.name, cst.Name) or alias.name.value != "sleep":
                continue
            self._time_sleep_alias_nodes.add(node)

    def visit_Assign(self, node: cst.Assign) -> None:
        for target in node.targets:
            if not isinstance(target.target, cst.Name):
                continue
            if self._is_time_sleep_expression(node.value):
                self._time_sleep_alias_nodes.add(target.target)
            else:
                self._time_sleep_alias_nodes.discard(target.target)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if not isinstance(node.target, cst.Name):
            return

        if node.value is not None and self._is_time_sleep_expression(node.value):
            self._time_sleep_alias_nodes.add(node.target)
        else:
            self._time_sleep_alias_nodes.discard(node.target)

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
        scope = self.get_metadata(ScopeProvider, expression, None)
        if scope is None:
            return False

        try:
            assignments = scope[expression.value]
        except KeyError:
            return False

        return bool(assignments) and all(
            getattr(assignment, "node", None) in self._time_sleep_alias_nodes
            for assignment in assignments
        )

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
