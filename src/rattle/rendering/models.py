from enum import Enum


class OutputFormat(str, Enum):
    custom = "custom"
    rattle = "rattle"
    vscode = "vscode"


__all__ = ["OutputFormat"]
