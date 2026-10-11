from enum import StrEnum


class OutputFormat(StrEnum):
    custom = "custom"
    rattle = "rattle"
    vscode = "vscode"


__all__ = ["OutputFormat"]
