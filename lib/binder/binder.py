from lib.data.catalog import *
from lib.query.commands import (
    Command,
    SelectCommand,
    InsertCommand,
    CreateTableCommand,
    DropTableCommand,
    UpdateCommand,
    DeleteCommand,
)

class Binder:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def resolve(self, ast_command: Command) -> bool:
        # CREATE TABLE defines a new table, so there's nothing to resolve
        # against the catalog yet.
        if isinstance(ast_command, CreateTableCommand):
            return True

        table_name, column_names = self._table_and_columns(ast_command)
        return self.resolve_table(table_name=table_name, column_names=column_names)

    def resolve_table(self, table_name: str, column_names: list[str]) -> bool:
        # Check if the table exists in the catalog
        table = self.catalog.get_table_or_none(table_name)
        if table is None:
            return False

        # Check if all column names exist in the table
        column_names_in_table = {col.name for col in table.columns}
        for col_name in column_names:
            if col_name not in column_names_in_table:
                return False

        return True

    def _table_and_columns(self, ast_command: Command) -> tuple[str, list[str]]:
        match ast_command:
            case SelectCommand():
                columns = [] if ast_command.columns == ['*'] else list(ast_command.columns)
                if ast_command.where_column is not None:
                    columns.append(ast_command.where_column)
                return ast_command.table, columns
            case InsertCommand():
                return ast_command.table, []
            case DropTableCommand():
                return ast_command.table, []
            case UpdateCommand():
                columns = [ast_command.set_column]
                if ast_command.where_column is not None:
                    columns.append(ast_command.where_column)
                return ast_command.table, columns
            case DeleteCommand():
                columns = [ast_command.where_column] if ast_command.where_column is not None else []
                return ast_command.table, columns