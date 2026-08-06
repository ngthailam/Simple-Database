import struct
from lib.data.pager import Pager, PAGE_SIZE
from lib.data.schema import ColumnDef, ColumnType
from lib.data.catalog import TableDef

MAX_DATA_PAGES = 200

# root page header: num_rows(4) + num_pages_used(4) + page_numbers[MAX_DATA_PAGES](4 each)
TABLE_HEADER_FORMAT = f'<ii{MAX_DATA_PAGES}i'
TABLE_HEADER_SIZE = struct.calcsize(TABLE_HEADER_FORMAT)

TYPE_TO_STRUCT_CHAR = {
    ColumnType.INT: 'i',
    ColumnType.TEXT: 's',
}

class Table:
    def __init__(self, pager: Pager, table_def: TableDef):
        self.pager = pager
        self.table_def = table_def
        self.root_page = table_def.root_page

        self.row_format, self.row_size = self._build_row_format(table_def.columns)
        self.rows_per_page = PAGE_SIZE // self.row_size

        header = self.pager.get_page(self.root_page)
        unpacked = struct.unpack_from(TABLE_HEADER_FORMAT, header, 0)
        self.num_rows = unpacked[0]
        self.num_pages_used = unpacked[1]
        self.page_numbers = list(unpacked[2:2 + self.num_pages_used])

    def _build_row_format(self, columns: list[ColumnDef]):
        fmt = '<'
        for col in columns:
            char = TYPE_TO_STRUCT_CHAR[col.type]
            fmt += f'{col.size}{char}' if char == 's' else char
        return fmt, struct.calcsize(fmt)

    def _get_data_page(self, page_index: int):
        if page_index < self.num_pages_used:
            return self.pager.get_page(self.page_numbers[page_index])

        if self.num_pages_used >= MAX_DATA_PAGES:
            raise ValueError(f"table '{self.table_def.name}' reached max pages ({MAX_DATA_PAGES})")

        new_page_num = self.pager.allocate_new_page()
        self.page_numbers.append(new_page_num)
        self.num_pages_used += 1
        return self.pager.get_page(new_page_num)

    def insert(self, values: list):
        packed_values = []
        for value, col in zip(values, self.table_def.columns):
            if col.type == ColumnType.TEXT:
                packed_values.append(value.encode('utf-8'))
            else:
                packed_values.append(value)

        row_bytes = struct.pack(self.row_format, *packed_values)

        page_index = self.num_rows // self.rows_per_page
        offset = (self.num_rows % self.rows_per_page) * self.row_size

        page = self._get_data_page(page_index)
        page[offset:offset + self.row_size] = row_bytes

        self.num_rows += 1

    def delete(self, where_column: str | None, where_value: object | None) -> int:
        write_index = 0
        deleted_count = 0

        for read_index in range(self.num_rows):
            read_page = self.pager.get_page(self.page_numbers[read_index // self.rows_per_page])
            read_offset = (read_index % self.rows_per_page) * self.row_size
            raw = struct.unpack_from(self.row_format, read_page, read_offset)

            satisfy_where_clause = where_column is None
            for value, col in zip(raw, self.table_def.columns):
                if col.type == ColumnType.TEXT:
                    value = value.rstrip(b'\x00').decode('utf-8')
                if where_column is not None and col.name == where_column and value == where_value:
                    satisfy_where_clause = True

            if satisfy_where_clause:
                deleted_count += 1
                continue

            # Keep this row: shift it down to the next free slot (write_index),
            # since earlier rows may have been dropped and left a gap.
            if write_index != read_index:
                write_page = self.pager.get_page(self.page_numbers[write_index // self.rows_per_page])
                write_offset = (write_index % self.rows_per_page) * self.row_size
                write_page[write_offset:write_offset + self.row_size] = \
                    read_page[read_offset:read_offset + self.row_size]
            write_index += 1

        self.num_rows = write_index
        return deleted_count

    def update(
        self,
        set_column: str,
        set_value: object,
        where_column: str | None,
        where_value: object | None,
    ) -> int:
        set_col_index = self._column_index(set_column)
        updated_count = 0

        for row_index in range(self.num_rows):
            page_index = row_index // self.rows_per_page
            offset = (row_index % self.rows_per_page) * self.row_size

            page = self.pager.get_page(self.page_numbers[page_index])
            raw = list(struct.unpack_from(self.row_format, page, offset))

            satisfy_where_clause = where_column is None
            for i, (value, col) in enumerate(zip(raw, self.table_def.columns)):
                if col.type == ColumnType.TEXT:
                    value = value.rstrip(b'\x00').decode('utf-8')

                if where_column is not None and col.name == where_column and value == where_value:
                    satisfy_where_clause = True

            if not satisfy_where_clause:
                continue

            set_col = self.table_def.columns[set_col_index]
            raw[set_col_index] = set_value.encode('utf-8') if set_col.type == ColumnType.TEXT else set_value

            row_bytes = struct.pack(self.row_format, *raw)
            page[offset:offset + self.row_size] = row_bytes
            updated_count += 1

        return updated_count

    def _column_index(self, column_name: str) -> int:
        for i, col in enumerate(self.table_def.columns):
            if col.name == column_name:
                return i
        raise ValueError(f"no such column: '{column_name}'")


    def select_all(
        self, 
        columns: list[str], 
        where_column: str | None,
        where_value: object | None
    ) -> list[tuple]:
        results = []
        for row_index in range(self.num_rows):
            page_index = row_index // self.rows_per_page
            offset = (row_index % self.rows_per_page) * self.row_size

            page = self.pager.get_page(self.page_numbers[page_index])
            raw = struct.unpack_from(self.row_format, page, offset)

            row = []
            satisfy_where_clause = where_column is None
            for value, col in zip(raw, self.table_def.columns):
                if col.type == ColumnType.TEXT:
                    value = value.rstrip(b'\x00').decode('utf-8')

                if where_column is not None and col.name == where_column:
                    if value == where_value:
                        satisfy_where_clause = True

                should_include_row = columns == ['*'] or col.name in columns
                if not should_include_row:
                    continue

                row.append(value)
            
            if satisfy_where_clause:
                results.append(tuple(row))
        return results

    def flush_header(self):
        header = self.pager.get_page(self.root_page)
        padded_pages = self.page_numbers + [0] * (MAX_DATA_PAGES - len(self.page_numbers))
        struct.pack_into(TABLE_HEADER_FORMAT, header, 0,
                          self.num_rows, self.num_pages_used, *padded_pages)
