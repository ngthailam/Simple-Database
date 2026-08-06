from lib.data.catalog import *

class Binder:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def resolve_table(self, table_name: str, column_names: list[str]) -> bool:
        return True