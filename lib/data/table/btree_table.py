import struct

from lib.data.pager import Pager
from lib.data.catalog import TableDef
from lib.data.schema import ColumnDef, ColumnType
from lib.data.btree.btree import BTree

TYPE_TO_STRUCT_CHAR = {
    ColumnType.INT: 'i',
    ColumnType.TEXT: 's',
}

class BTreeTable:
    def __init__(self, pager: Pager, table_def: TableDef):
        self.pager = pager
        self.table_def = table_def
        self.primary_column_index = self._find_primary_column_index()
        self.row_format, self.row_size = self._build_row_format(table_def.columns) 
        self.btree = BTree(pager, table_def, value_size=self.row_size)

    def _find_primary_column_index(self) -> int | None:
        for i, col in enumerate(self.table_def.columns):
            if col.is_primary:
                return i
        return None

    def _build_row_format(self, columns: list[ColumnDef]):
        fmt = '<'
        for col in columns:
            char = TYPE_TO_STRUCT_CHAR[col.type]
            fmt += f'{col.size}{char}' if char == 's' else char
        return fmt, struct.calcsize(fmt)

    def _column_index(self, column_name: str) -> int:
        for i, col in enumerate(self.table_def.columns):
            if col.name == column_name:
                return i
        raise ValueError(f"no such column: '{column_name}'")

    def _serialize_row(self, values: list) -> bytes:
        packed_values = []
        for value, col in zip(values, self.table_def.columns):
            if col.type == ColumnType.TEXT:
                value_bytes = value.encode('utf-8')
                if len(value_bytes) > col.size:
                    raise ValueError(f"value for column '{col.name}' too long (max {col.size} bytes)")
                packed_values.append(value_bytes)
            else:
                packed_values.append(value)

        row_bytes = struct.pack(self.row_format, *packed_values)
        if len(row_bytes) > self.btree.leaf_entry_size:
            raise ValueError(f"serialized row too large ({len(row_bytes)} bytes, max {self.btree.leaf_entry_size})")
        return row_bytes

    def _deserialize_row(self, row_bytes: bytes) -> tuple:
        raw = struct.unpack_from(self.row_format, row_bytes, 0)
        row = []
        for value, col in zip(raw, self.table_def.columns):
            if col.type == ColumnType.TEXT:
                value = value.rstrip(b'\x00').decode('utf-8')
            row.append(value)
        return tuple(row)

    def insert(self, values: list):
        if self.primary_column_index is None:
            raise NotImplementedError("BTreeTable requires a primary key column")

        key = values[self.primary_column_index]
        row_bytes = self._serialize_row(values)
        self.btree.insert(key, row_bytes)
        
    def insert_all(self, values: list[list]):
        if self.primary_column_index is None:
                raise NotImplementedError("BTreeTable requires a primary key column")
            
        items = []
        for v in values:
            item_key = v[self.primary_column_index]
            item_row_bytes = self._serialize_row(v)

            items.append((item_key, item_row_bytes))
            
        self.btree.insert_all(items)

    def delete(self, where_column: str | None, where_value: object | None) -> int:
        if self.primary_column_index is None:
            raise NotImplementedError("BTreeTable requires a primary key column")

        # Delete by primary key column (Unique => delete 1 record only)
        if where_column is not None and self._column_index(where_column) == self.primary_column_index:
            removed = self.btree.delete(where_value)
            return 1 if removed is not None else 0
        
        # Delete * (without WHERE) => Reset the table instead, to improve performance
        if where_column is None:
            deleted_count = self.btree.delete_all()
            self.btree.reset()
            return deleted_count

        # Delete multiple
        def predicate(row_bytes: bytes) -> bool:
            row = self._deserialize_row(row_bytes)
            return self._matches_where(row, where_column, where_value)

        return self.btree.delete_where(predicate)

    def update(
        self,
        set_column: str,
        set_value: object,
        where_column: str | None,
        where_value: object | None,
    ) -> int:
        if self.primary_column_index is None:
            raise NotImplementedError("BTreeTable requires a primary key column")

        set_col_index = self._column_index(set_column)
        if set_col_index == self.primary_column_index:
            raise NotImplementedError("Updating the primary key column is not supported")

        updated_count = 0
        for key, row_bytes in list(self.btree.scan()):
            row = self._deserialize_row(row_bytes)
            if not self._matches_where(row, where_column, where_value):
                continue

            new_values = list(row)
            new_values[set_col_index] = set_value
            new_row_bytes = self._serialize_row(new_values)
            self.btree.delete(key)
            self.btree.insert(key, new_row_bytes)
            updated_count += 1
        return updated_count

    def select_all(
        self,
        columns: list[str],
        where_column: str | None,
        where_value: object | None
    ) -> list[tuple]:
        if self.primary_column_index is None:
            raise NotImplementedError("BTreeTable requires a primary key column")

        def project(row: tuple) -> tuple:
            if columns == ['*']:
                return row
            return tuple(
                value for value, col in zip(row, self.table_def.columns)
                if col.name in columns
            )

        if where_column is not None and self._column_index(where_column) == self.primary_column_index:
            row_bytes = self.btree.search(where_value)
            if row_bytes is None:
                return []
            return [project(self._deserialize_row(row_bytes))]

        results = []
        for _, row_bytes in self.btree.scan():
            row = self._deserialize_row(row_bytes)
            if not self._matches_where(row, where_column, where_value):
                continue
            results.append(project(row))
        return results

    def _matches_where(self, row: tuple, where_column: str | None, where_value: object | None) -> bool:
        if where_column is None:
            return True
        col_index = self._column_index(where_column)
        return row[col_index] == where_value

    def flush_header(self):
        pass
