import struct

# --- engine.py ---
DB_FILE = 'test_e2e.db'

# --- server.py ---
HOST = '127.0.0.1'
PORT = 5432

# --- lib/data/pager.py ---
HEADER_PAGE = 0
PAGE_SIZE = 4096  # 4KB
MAX_PAGES = 5_000_000_000

# --- lib/data/schema.py ---
NAME_MAX_BYTES = 16
TYPE_MAX_BYTES = 1
SIZE_MAX_BYTES = 4  # int denoting the size of the column's value
IS_PRIMARY_MAX_BYTES = 1  # bool denoting if the column is primary key

# --- lib/data/catalog.py ---
MAX_TABLES = 20
MAX_COLUMNS = 8
NAME_SIZE = 16

CATALOG_HEADER_FORMAT = '<i'  # num_tables_used
CATALOG_HEADER_SIZE = struct.calcsize(CATALOG_HEADER_FORMAT)  # 4

COLUMN_SLOT_FORMAT = f'<{NAME_SIZE}sBiB'  # name, type (1 byte unsigned), size, is_primary (1 byte unsigned)
COLUMN_SLOT_SIZE = struct.calcsize(COLUMN_SLOT_FORMAT)  # 22

TABLE_ENTRY_FORMAT = f'<{NAME_SIZE}sii'  # name, root_page, num_columns_used
TABLE_ENTRY_HEADER_SIZE = struct.calcsize(TABLE_ENTRY_FORMAT)  # 16 + 4 + 4 = 24
TABLE_ENTRY_SIZE = TABLE_ENTRY_HEADER_SIZE + MAX_COLUMNS * COLUMN_SLOT_SIZE  # 24 + 168 = 192

# Catalog size = CATALOG_HEADER_SIZE + MAX_TABLES * TABLE_ENTRY_SIZE
#              = 4 + 20*192
#              = 4 + 3840
#              = 3844 bytes  (fits in one 4096-byte page)

# --- lib/data/tree/table.py ---
MAX_DATA_PAGES = 200

# root page header: num_rows(4) + num_pages_used(4) + page_numbers[MAX_DATA_PAGES](4 each)
TABLE_HEADER_FORMAT = f'<ii{MAX_DATA_PAGES}i'
TABLE_HEADER_SIZE = struct.calcsize(TABLE_HEADER_FORMAT)

# --- lib/data/row.py ---
ROW_FORMAT = '<i32s255s'  # little-endian, 4-byte int, 32-byte string, 255-byte string
ROW_SIZE = struct.calcsize(ROW_FORMAT)  # 4 + 32 + 255 = 291 bytes

# BTree
BTREE_HEADER_FORMAT = '<i' # root_page (4 bytes)

BNODE_LEAF_HEADER_FORMAT = '<BHi' # is_leaf(1), num_keys(2), next_leaf_page_number (4)
BNODE_LEAF_HEADER_OFFSET = struct.calcsize(BNODE_LEAF_HEADER_FORMAT)
BNODE_LEAF_VALUE_MAX_BYTES = PAGE_SIZE - BNODE_LEAF_HEADER_OFFSET - struct.calcsize('<i')

BNODE_INTERNAL_HEADER_FORMAT = '<BHi' # is_leaf(1), num_keys(2), leftmost_child_page (4)
BNODE_INTERNAL_HEADER_OFFSET = struct.calcsize(BNODE_INTERNAL_HEADER_FORMAT)
BNODE_INTERNAL_ENTRY_FORMAT = '<ii' # key (4 bytes), child_page (4 bytes)
BNODE_INTERNAL_ENTRY_SIZE = struct.calcsize(BNODE_INTERNAL_ENTRY_FORMAT)
INTERNAL_MAX_KEYS = (PAGE_SIZE - BNODE_INTERNAL_HEADER_OFFSET) // BNODE_INTERNAL_ENTRY_SIZE

# Insert
INSERT_ALL_REBUILD_THRESHOLD = 2500