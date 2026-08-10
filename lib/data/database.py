from lib.data.pager import Pager, PAGE_SIZE
from lib.data.catalog import Catalog, MAX_TABLES, MAX_COLUMNS
from lib.data.schema import ColumnDef, ColumnType
from lib.data.table.btree_table import BTreeTable

class Database:
    def __init__(self, pager: Pager, catalog: Catalog):
        self.pager = pager
        self.catalog = catalog
        self.open_tables: dict[str, BTreeTable] = {}

    def create_table(self, name: str, columns: list[ColumnDef]):
        root_page = self.pager.allocate_new_page()
        table_def = self.catalog.create_table(name, columns, root_page)
        self.open_tables[name] = BTreeTable(self.pager, table_def)
        return table_def
    
    def delete_table(self, name: str):
        self.catalog.delete_table(name)
        self.open_tables.pop(name, None)

    def insert(self, table_name: str, values: list):
        table = self._get_table(table_name)
        table.insert(values)

    def insert_all(self, table_name: str, rows: list[list]):
        table = self._get_table(table_name)
        table.insert_all(rows)

    def select_all(self, 
        table_name: str, 
        columns: list[str], 
        where_column: str | None,
        where_value: object | None
    ) -> list[tuple]:
        table = self._get_table(table_name)
        return table.select_all(columns, where_column, where_value)

    def update(
        self,
        table_name: str,
        set_column: str,
        set_value: object,
        where_column: str | None,
        where_value: object | None,
    ) -> int:
        table = self._get_table(table_name)
        return table.update(set_column, set_value, where_column, where_value)
    
    def delete(self, table_name: str, where_column: str | None, where_value: object | None) -> int:
        table = self._get_table(table_name)
        return table.delete(where_column, where_value)

    def flush(self):
        for table in self.open_tables.values():
            table.flush_header()  # persist e.g. num_rows
        self.pager.flush_all()

    def close(self):
        self.flush()
        self.pager.close()

    # Private methods
    def _get_table(self, name: str) -> BTreeTable:
        if name not in self.open_tables:
            table_def = self.catalog.get_table(name)
            self.open_tables[name] = BTreeTable(self.pager, table_def)
        return self.open_tables[name]
