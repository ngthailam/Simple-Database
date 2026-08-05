from dataclasses import dataclass
from data.schema import ColumnDef


class Command:
    pass


@dataclass
class SelectCommand(Command):
    table: str
    columns: list[str]          # e.g. ['*'] or ['id', 'email']
    where_column: str | None    # None = no WHERE clause (full scan)
    where_value: object | None


@dataclass
class InsertCommand(Command):
    table: str
    values: list


@dataclass
class CreateTableCommand(Command):
    table: str
    columns: list[ColumnDef]


@dataclass
class DropTableCommand(Command):
    table: str


@dataclass
class UpdateCommand(Command):
    table: str
    set_column: str
    set_value: object
    where_column: str | None
    where_value: object | None


@dataclass
class DeleteCommand(Command):
    table: str
    where_column: str | None
    where_value: object | None
