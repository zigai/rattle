# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import libcst as cst
from libcst.metadata import QualifiedNameProvider

from rattle import Invalid, LintRule, Valid


class UseAsyncSleepInAsyncDef(LintRule):
    CODE = "RAT022"
    """Detect if asyncio.sleep is used in an async function."""

    MESSAGE: str = "Use asyncio.sleep in async function"
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)
    VALID = [
        Valid(
            """
            import time
            def func():
                time.sleep(1)
            """
        ),
        Valid(
            """
            from time import sleep
            def func():
                sleep(1)
            """
        ),
        Valid(
            """
            from asyncio import sleep
            async def func():
                await sleep(1)
            """
        ),
        Valid(
            """
            import asyncio
            async def func():
                await asyncio.sleep(1)
            """
        ),
        Valid(
            """
            import time
            import asyncio
            def func():
                time.sleep(1)
            """
        ),
        Valid(
            """
            import time
            import asyncio
            async def func():
                await asyncio.sleep(1)
            """
        ),
        Valid(
            """
            import time
            import asyncio
            async def func():
                fut = asyncio.sleep(1)
                await fut
            """
        ),
        Valid(
            """
            import something
            async def func():
                something.sleep(3)
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            import time
            async def func():
                time.sleep(1)
            """
        ),
        Invalid(
            """
            from time import sleep
            async def func():
                sleep(1)
            """
        ),
        Invalid(
            """
            from time import sleep
            import asyncio
            async def func():
                sleep(2)
                asyncio.sleep(1)
            """
        ),
        Invalid(
            """
            from asyncio import sleep
            import time
            async def func():
                sleep(2)
                time.sleep(1)
            """
        ),
        Invalid(
            """
            import time
            async def outer():
                def inner():
                    pass
                time.sleep(1)
            """
        ),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.function_stack: list[bool] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self.function_stack.append(node.asynchronous is not None)

    def leave_FunctionDef(self, _original_node: cst.FunctionDef) -> None:
        self.function_stack.pop()

    def visit_Call(self, node: cst.Call) -> None:
        if not self.function_stack or not self.function_stack[-1]:
            return

        metadata = list(self.get_metadata(QualifiedNameProvider, node, ()))
        if not metadata:
            return

        func_full_name = metadata[0].name
        if func_full_name != "time.sleep":
            return

        self.report(node, self.MESSAGE)
