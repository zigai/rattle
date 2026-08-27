"""Typing rules for annotations and modern type syntax."""

from rattle.rules.typing.no_any_container_annotations import NoAnyContainerAnnotations
from rattle.rules.typing.no_any_type_aliases import NoAnyTypeAliases
from rattle.rules.typing.no_bare_object_annotations import NoBareObjectAnnotations
from rattle.rules.typing.no_casts_to_never import NoCastsToNever
from rattle.rules.typing.no_chained_casts import NoChainedCasts
from rattle.rules.typing.no_known_value_to_any import NoKnownValueToAny
from rattle.rules.typing.no_object_mapping_values import NoObjectMappingValues
from rattle.rules.typing.no_widen_then_cast import NoWidenThenCast
from rattle.rules.typing.require_safety_comment_for_cast import RequireSafetyCommentForCast
from rattle.rules.typing.use_types_from_typing import UseTypesFromTyping
from rattle.rules.typing.variadic_callable_syntax import VariadicCallableSyntax

__all__ = [
    "NoAnyContainerAnnotations",
    "NoAnyTypeAliases",
    "NoBareObjectAnnotations",
    "NoCastsToNever",
    "NoChainedCasts",
    "NoKnownValueToAny",
    "NoObjectMappingValues",
    "NoWidenThenCast",
    "RequireSafetyCommentForCast",
    "UseTypesFromTyping",
    "VariadicCallableSyntax",
]
