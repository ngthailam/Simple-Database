import struct
from data.pager import Pager, PAGE_SIZE
from data.schema import ColumnDef, ColumnType
from data.catalog import TableDef

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

    def select_all(self) -> list[tuple]:
        results = []
        for row_index in range(self.num_rows):
            page_index = row_index // self.rows_per_page
            offset = (row_index % self.rows_per_page) * self.row_size

            page = self.pager.get_page(self.page_numbers[page_index])
            raw = struct.unpack_from(self.row_format, page, offset)

            row = []
            for value, col in zip(raw, self.table_def.columns):
                if col.type == ColumnType.TEXT:
                    row.append(value.rstrip(b'\x00').decode('utf-8'))
                else:
                    row.append(value)
            results.append(tuple(row))
        return results

    def flush_header(self):
        header = self.pager.get_page(self.root_page)
        padded_pages = self.page_numbers + [0] * (MAX_DATA_PAGES - len(self.page_numbers))
        struct.pack_into(TABLE_HEADER_FORMAT, header, 0,
                          self.num_rows, self.num_pages_used, *padded_pages)
