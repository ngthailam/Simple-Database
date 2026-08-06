from lib.data.catalog import *

class Binder:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def resolve_table(self, table_name: str, column_names: list[str]) -> bool:
        # Check if the table exists in the catalog
        table = self.catalog.get_table_or_none(table_name)
        if table is None:
            return False
        
        # Check if all column names exist in the table
        columns = table.columns
        for col_name in column_names:
            if col_name not in columns:
                return False 
        
        return True