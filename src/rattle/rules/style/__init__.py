"""Opinionated style rules that are not inherited from Fixit."""

from rattle.rules.style.no_annotated_self import NoAnnotatedSelf
from rattle.rules.style.public_method_order import PublicMethodOrder

__all__ = [
    "NoAnnotatedSelf",
    "PublicMethodOrder",
]
