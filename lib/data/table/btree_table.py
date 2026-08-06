from lib.data.pager import Pager
from lib.data.catalog import TableDef
from lib.data.table.table_interface import TableInterface

# Placeholder B-Tree-backed Table implementation.
# Implements TableInterface, same as lib/data/tree/table.py's Table,
# so Database can use either implementation interchangeably. Not implemented yet.

class BTreeTable(TableInterface):
    def __init__(self, pager: Pager, table_def: TableDef):
        self.pager = pager
        self.table_def = table_def
        self.root_page = table_def.root_page

    def insert(self, values: list):
        raise NotImplementedError

    def delete(self, where_column: str | None, where_value: object | None) -> int:
        raise NotImplementedError

    def update(
        self,
        set_column: str,
        set_value: object,
        where_column: str | None,
        where_value: object | None,
    ) -> int:
        raise NotImplementedError

    def select_all(
        self,
        columns: list[str],
        where_column: str | None,
        where_value: object | None
    ) -> list[tuple]:
        raise NotImplementedError

    def flush_header(self):
        raise NotImplementedError
