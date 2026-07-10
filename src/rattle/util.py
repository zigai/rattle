# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Generic, TypeVar

Yield = TypeVar("Yield")
Send = TypeVar("Send")
Return = TypeVar("Return")


class MissingGeneratorValue:
    pass


MISSING_GENERATOR_VALUE = MissingGeneratorValue()


class Capture(Generic[Yield, Send, Return]):
    """
    Wrap a generator, and capture it's final return value in the :attr:`result` property.

    Allows sending values back to the generator using the :meth:`respond` method.

    Example usage:

    .. code:: python

        generator = capture( rattle_bytes(...) )
        for result in generator:  # LintViolation
            ...
            generator.respond(...)  # optional

        result = generator.result  # FileContent
    """

    def __init__(self, generator: Generator[Yield, Send, Return]) -> None:
        self.generator = generator
        self._response: Send | MissingGeneratorValue = MISSING_GENERATOR_VALUE
        self._result: Return | MissingGeneratorValue = MISSING_GENERATOR_VALUE

    def __iter__(self) -> Generator[Yield, Send, Return]:
        try:
            while True:
                if isinstance(self._response, MissingGeneratorValue):
                    value = next(self.generator)
                else:
                    response = self._response
                    self._response = MISSING_GENERATOR_VALUE
                    value = self.generator.send(response)
                answer = yield value
                if answer is not None:
                    self._response = answer
        except StopIteration as e:
            self._result = e.value
            return e.value

    def respond(self, answer: Send) -> None:
        """
        Send a value back to the generator in the next iteration.

        Can be called while iterating on the wrapped generator object.
        """
        self._response = answer

    @property
    def result(self) -> Return:
        """Contains the final return value from the wrapped generator, if any."""
        if isinstance(self._result, MissingGeneratorValue):
            raise TypeError("Generator hasn't completed")
        return self._result


capture = Capture


@contextmanager
def append_sys_path(path: Path) -> Generator[None, None, None]:
    """
    Append a path to ``sys.path`` temporarily, and then remove it again when done.

    If the given path is already in ``sys.path``, it will not be added a second time,
    and it will not be removed when leaving the context.
    """
    path_str = path.as_posix()

    # not there: append to path, and remove it when leaving the context
    if path_str not in sys.path:
        sys.path.append(path_str)
        yield
        sys.path.remove(path_str)

    # already there: do nothing, and don't remove it later
    else:
        yield


@contextmanager
def chdir(path: Path) -> Generator[None, None, None]:
    cwd = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


__all__ = [
    "Capture",
    "append_sys_path",
    "capture",
    "chdir",
]
