"""Typing rules for annotations and modern type syntax."""

from rattle.rules.typing.no_bare_object_annotations import NoBareObjectAnnotations
from rattle.rules.typing.use_types_from_typing import UseTypesFromTyping
from rattle.rules.typing.variadic_callable_syntax import VariadicCallableSyntax

__all__ = [
    "NoBareObjectAnnotations",
    "UseTypesFromTyping",
    "VariadicCallableSyntax",
]
