from enum import Enum
from dataclasses import dataclass

NAME_MAX_BYTES = 16
TYPE_MAX_BYTES = 1
SIZE_MAX_BYTES = 4  # int denoting the size of the column's value

class ColumnType(Enum):
    INT = 1
    TEXT = 2

@dataclass
class ColumnDef:
    name: str
    type: ColumnType
    size: int

    def get_size_bytes(self):
        return NAME_MAX_BYTES + TYPE_MAX_BYTES + SIZE_MAX_BYTES

@dataclass
class TableDef:
    name: str
    root_page: int
    columns: list[ColumnDef]