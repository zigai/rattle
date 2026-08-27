from rattle.rule import Invalid, Valid
from rattle.rules.typing import _container_annotations


class NoObjectMappingValues(_container_annotations.ContainerAnnotationRule):
    """Disallow broad ``object`` value types in standard mapping annotations."""

    MESSAGE = (
        "Replace this broad `object` mapping value with a concrete value type or parsed owner type."
    )
    TARGET = "builtins.object"
    MAPPING_VALUES_ONLY = True

    VALID = [
        Valid(
            """
            values: dict[object, str]
            items: list[object]
            """
        ),
        Valid(
            """
            class object:
                pass

            values: dict[str, object]
            """
        ),
    ]
    INVALID = [
        Invalid(
            """
            values: dict[str, object]
            """,
            expected_message=MESSAGE,
        ),
        Invalid(
            """
            from collections.abc import Mapping
            from typing import Annotated

            values: Mapping[str, Annotated[object, "decoded later"]]
            """,
            expected_message=MESSAGE,
        ),
    ]
