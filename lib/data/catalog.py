from lib.data.pager import Pager, PAGE_SIZE
from lib.data.schema import *
import struct

from lib.utils.constants import (
    HEADER_PAGE,
    MAX_TABLES,
    MAX_COLUMNS,
    NAME_SIZE,
    CATALOG_HEADER_FORMAT as HEADER_FORMAT,
    CATALOG_HEADER_SIZE as HEADER_SIZE,
    COLUMN_SLOT_FORMAT,
    COLUMN_SLOT_SIZE,
    TABLE_ENTRY_FORMAT,
    TABLE_ENTRY_HEADER_SIZE,
    TABLE_ENTRY_SIZE,
)

# Catalog size = HEADER_SIZE + MAX_TABLES * TABLE_ENTRY_SIZE
#              = 4 + 20*192
#              = 4 + 3840
#              = 3844 bytes  (fits in one 4096-byte page)

class Catalog:
    def __init__(self, pager: Pager):
        self.pager = pager
        header_page = pager.get_page(HEADER_PAGE)

        self.num_tables_used, = struct.unpack_from(HEADER_FORMAT, header_page, 0)

        self.tables: dict[str, TableDef] = {}
        for i in range(self.num_tables_used):
            entry_offset = HEADER_SIZE + i * TABLE_ENTRY_SIZE
            name_bytes, root_page, num_columns_used = struct.unpack_from(
                TABLE_ENTRY_FORMAT, header_page, entry_offset
            )
            table_name = name_bytes.rstrip(b'\x00').decode('utf-8')

            columns = []
            for j in range(num_columns_used):
                col_offset = entry_offset + TABLE_ENTRY_HEADER_SIZE + j * COLUMN_SLOT_SIZE
                col_name_bytes, col_type, col_size, col_is_primary = struct.unpack_from(
                    COLUMN_SLOT_FORMAT, header_page, col_offset
                )
                columns.append(ColumnDef(
                    col_name_bytes.rstrip(b'\x00').decode('utf-8'),
                    ColumnType(col_type),
                    col_size,
                    bool(col_is_primary)
                ))

            self.tables[table_name] = TableDef(table_name, root_page, columns)

    def get_table_or_none(self, name: str) -> TableDef | None:
        return self.tables.get(name)

    def get_table(self, name: str) -> TableDef:
        table = self.get_table_or_none(name)
        if table is None:
            raise ValueError(f"no such table: '{name}'")
        return table
    
    def create_table(self, name: str, columns: list[ColumnDef], root_page: int) -> TableDef:
        if self.get_table_or_none(name) is not None:
            raise ValueError(f"table '{name}' already exists")
        if self.num_tables_used >= MAX_TABLES:
            raise ValueError("max tables reached")
        if len(columns) > MAX_COLUMNS:
            raise ValueError(f"table '{name}' has too many columns (max {MAX_COLUMNS})")
            
        name_bytes = name.encode('utf-8')
        if len(name_bytes) > NAME_SIZE:
            raise ValueError(f"table name '{name}' too long (max {NAME_SIZE} bytes)")
        
        entry_offset = HEADER_SIZE + (self.num_tables_used * TABLE_ENTRY_SIZE)

        self.pager.pack_into(HEADER_PAGE, entry_offset, TABLE_ENTRY_FORMAT, name_bytes, root_page, len(columns))

        for j, col in enumerate(columns):
            col_name_bytes = col.name.encode('utf-8')
            if len(col_name_bytes) > NAME_SIZE:
                raise ValueError(f"column name '{col.name}' too long (max {NAME_SIZE} bytes)")

            col_is_primary_bytes = 1 if col.is_primary else 0
            col_offset = entry_offset + TABLE_ENTRY_HEADER_SIZE + j * COLUMN_SLOT_SIZE

            self.pager.pack_into(HEADER_PAGE, col_offset, COLUMN_SLOT_FORMAT, col_name_bytes, col.type.value, col.size, col_is_primary_bytes)

        self.num_tables_used += 1
        self.pager.pack_into(HEADER_PAGE, 0, HEADER_FORMAT, self.num_tables_used)

        table_def = TableDef(name, root_page, columns)
        self.tables[name] = table_def
        return table_def

    def delete_table(self, name: str):
        if name not in self.tables:
            raise ValueError(f"no such table: '{name}'")

        # self.tables preserves insertion order, which matches the physical
        # slot order in the header page — use it to find this table's slot index.
        index = list(self.tables.keys()).index(name)
        header_page = self.pager.get_page(HEADER_PAGE)

        # Shift every later entry down one slot to keep entries dense (slots
        # 0..num_tables_used-1), since num_tables_used assumes no gaps.
        for i in range(index, self.num_tables_used - 1):
            src_offset = HEADER_SIZE + (i + 1) * TABLE_ENTRY_SIZE
            dst_offset = HEADER_SIZE + i * TABLE_ENTRY_SIZE
            self.pager.write_bytes(
                HEADER_PAGE, dst_offset,
                bytes(header_page[src_offset:src_offset + TABLE_ENTRY_SIZE])
            )

        # Zero out the now-unused last slot.
        last_offset = HEADER_SIZE + (self.num_tables_used - 1) * TABLE_ENTRY_SIZE
        self.pager.write_bytes(HEADER_PAGE, last_offset, bytes(TABLE_ENTRY_SIZE))

        self.num_tables_used -= 1
        self.pager.pack_into(HEADER_PAGE, 0, HEADER_FORMAT, self.num_tables_used)

        del self.tables[name]