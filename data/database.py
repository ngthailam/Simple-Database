from data.pager import Pager, PAGE_SIZE
from data.catalog import Catalog, MAX_TABLES, MAX_COLUMNS
from data.schema import ColumnDef, ColumnType
from data.table import Table

class Database:
    def __init__(self, filename: str):
        self.pager = Pager(filename)
        self.catalog = Catalog(self.pager)
        self.open_tables: dict[str, Table] = {}

    def create_table(self, name: str, columns: list[ColumnDef]):
        root_page = self.pager.allocate_new_page()
        table_def = self.catalog.create_table(name, columns, root_page)
        self.open_tables[name] = Table(self.pager, table_def)
        return table_def

    def insert(self, table_name: str, values: list):
        table = self._get_table(table_name)
        table.insert(values)

    def select_all(self, table_name: str) -> list[tuple]:
        table = self._get_table(table_name)
        return table.select_all()

    def close(self):
        for table in self.open_tables.values():
            table.flush_header()  # persist e.g. num_rows, without closing shared pager
        self.pager.close()

    # Private methods
    def _get_table(self, name: str) -> Table:
        if name not in self.open_tables:
            table_def = self.catalog.get_table(name)
            self.open_tables[name] = Table(self.pager, table_def)
        return self.open_tables[name]
