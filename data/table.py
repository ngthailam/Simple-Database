import struct
from data.pager import Pager, PAGE_SIZE
from data.row import ROW_FORMAT, ROW_SIZE, serialize_row, deserialize_row

ROWS_PER_PAGE = PAGE_SIZE // ROW_SIZE

HEADER_PAGE = 0
DATA_PAGE_OFFSET = 1 # use page 0 as meta data

class Table:
    def __init__(self, filename: str):
        self.pager = Pager(filename)
        header = self.pager.get_page(HEADER_PAGE)
        self.num_rows = struct.unpack_from('<i', header, 0)[0]

    def insert(self, id: int, username: str, email: str):
        page_num = DATA_PAGE_OFFSET + (self.num_rows // ROWS_PER_PAGE)
        offset = (self.num_rows % ROWS_PER_PAGE) * ROW_SIZE
        end_offset = offset + ROW_SIZE

        page = self.pager.get_page(page_num)
        row_bytes = serialize_row(id, username, email)
        page[offset:end_offset] = row_bytes

        self.num_rows += 1

    def select_all(self) -> list[tuple[int, str, str]]:
        results = []
        for row_index in range(self.num_rows):
            page_num = DATA_PAGE_OFFSET + (row_index // ROWS_PER_PAGE)
            offset = (row_index % ROWS_PER_PAGE) * ROW_SIZE
            end_offset = offset + ROW_SIZE

            page = self.pager.get_page(page_num)
            row_bytes = bytes(page[offset:end_offset])
            results.append(deserialize_row(row_bytes))

        return results
    
    def close(self):
        header = self.pager.get_page(HEADER_PAGE)
        struct.pack_into('<i', header, 0, self.num_rows)
        self.pager.close()
        
if __name__ == '__main__':
    table = Table('mydb.db')
    table.insert(1, 'alice', 'alice@example.com')
    table.insert(2, 'bob', 'bob@example.com')
    print(table.select_all())
    table.close()

    # reopen to confirm persistence
    table2 = Table('mydb.db')
    print(table2.select_all())
    table2.insert(3, 'carol', 'carol@example.com')
    print(table2.select_all())
    table2.close()