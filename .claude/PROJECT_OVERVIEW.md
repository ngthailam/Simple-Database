# db-playground

A toy SQL database engine built from scratch in Python, for learning how databases work internally (paging, on-disk storage, catalog/schema management, and a minimal SQL pipeline). Not production code — no indexes, no transactions, no real query planning.

## How it runs

- `main.py` — REPL: reads a line of SQL from stdin, passes it to `Engine`, prints the result. Type `quit` to exit.
- `server.py` — TCP server (127.0.0.1:5432) that does the same over a socket connection, one `Engine` shared across connections.
- `scripts/reset_and_seed.py` — wipes `test_e2e.db` and recreates + seeds 5 tables (users, products, orders, reviews, sessions) with random rows, for manual testing/exploration.

## Request pipeline (`engine.py`)

`Engine.handle_command(sql_string)` runs each query through fixed stages:

1. `get_query_type` (`lib/query/query_type.py`) — detects SELECT/INSERT/CREATE TABLE/DROP TABLE/UPDATE/DELETE from the string prefix.
2. `QueryValidator.validate` (`lib/query/query_validator.py`) — syntax validation stub; currently always returns `True` (not implemented).
3. `Binder.resolve_table` (`lib/binder/binder.py`) — checks a table/columns exist in the catalog. **Note: currently called with hardcoded `table_name="s"`, `column_names=[]`, i.e. not actually wired to the real parsed command — effectively a no-op/placeholder.**
4. `Optimizer.optimize` (`lib/optimizer/optimizer.py`) — placeholder, currently just returns the input command unchanged.
5. `BasicAst.parse` (`lib/sqlast/basic_ast.py`) — regex-based parser that turns the SQL string into a `Command` dataclass (see below).
6. `Engine.exec_db_by_type` — pattern-matches on the `Command` type and calls the matching `Database` method.
7. For mutating commands (CREATE/INSERT/DELETE/UPDATE/DROP), `db.flush()` persists changes to disk.

## Folder structure

```
engine.py              Orchestrates the pipeline above; Engine.handle_command() is the main entrypoint
main.py                REPL entrypoint
server.py              TCP server entrypoint
scripts/
  reset_and_seed.py    Rebuilds test_e2e.db with sample data
lib/
  query/
    query_type.py      QueryType enum + prefix-based detection from raw SQL
    query_validator.py Syntax validation (stub, always passes)
    commands.py         Command dataclasses: SelectCommand, InsertCommand, CreateTableCommand,
                         DropTableCommand, UpdateCommand, DeleteCommand
  sqlast/
    basic_ast.py        Regex-based SQL parser: raw string -> Command dataclass
  binder/
    binder.py            Resolves table/column names against the Catalog (existence checks only)
  optimizer/
    optimizer.py         Query optimization (stub, currently identity function)
  data/
    pager.py             Pager: reads/writes fixed-size 4KB pages to/from the .db file, in-memory page cache
    schema.py             ColumnType enum (INT/TEXT), ColumnDef, TableDef dataclasses
    catalog.py             Catalog: table/column metadata stored in page 0 (header page) of the db file;
                            create/get/delete table definitions
    table.py               Table: row storage/retrieval within a table's data pages (fixed-width rows via
                            struct packing); insert/select_all/update/delete, all via full scans
    database.py            Database: ties Pager + Catalog + Table together; the storage-layer API Engine calls into
    row.py                 Older/simpler standalone row serialize helpers (fixed 3-column format) — appears
                            superseded by table.py's per-table dynamic row format; check before extending
test/
  test.py                 (currently empty)
  query/query_type_test.py  Unit tests for QueryType/get_query_type
```

## Storage model

- Everything lives in one file (default `test_e2e.db`), divided into fixed 4096-byte pages (`lib/data/pager.py`).
- Page 0 is the **catalog/header page**: table names, root page pointers, and column definitions (`lib/data/catalog.py`), packed via `struct`. Limits: `MAX_TABLES=20`, `MAX_COLUMNS=8`, 16-byte names.
- Each table has a **root page** storing a small header (num_rows, num_pages_used, list of data page numbers) plus, in the same table's data pages, fixed-width packed rows (`lib/data/table.py`). Row layout is derived per-table from its column defs (INT=4 bytes, TEXT=fixed size given at CREATE TABLE time).
- All scans (SELECT/UPDATE/DELETE) are full table scans — no indexes.

## Supported SQL (regex-parsed, simplified)

- `SELECT col1, col2 | * FROM table [WHERE col = value]`
- `INSERT INTO table VALUES (v1, v2, ...)`
- `CREATE TABLE table (col1 INT, col2 TEXT(size), ...)`
- `DROP TABLE table`
- `UPDATE table SET col = value [WHERE col = value]`
- `DELETE FROM table [WHERE col = value]`

WHERE only supports a single `col = value` equality condition. Values are either quoted strings (`'text'`) or bare integers.

## Known gaps / stubs (worth knowing before extending)

- `QueryValidator.validate` always returns `True` — no real syntax validation.
- `Optimizer.optimize` is an identity function — no real optimization.
- `Binder.resolve_table` is called with hardcoded dummy args in `engine.py`, not the actual parsed table/columns — effectively dead validation right now.
- `lib/data/row.py` looks like an early prototype (fixed id/username/email row format) that predates the generic per-table format in `table.py`; unclear if still used anywhere — verify before relying on it.
- No transactions, no concurrency control, no indexes — every query is a full scan.
