# db-playground

A toy SQL database engine built from scratch in Python — for learning how databases work internally (paging, on-disk storage, catalog/schema management, and a minimal SQL pipeline). Not production code: no indexes yet, no transactions, no real query planning.

For a deeper architecture overview (folder structure, storage model, pipeline stages, known gaps), see [.claude/PROJECT_OVERVIEW.md](.claude/PROJECT_OVERVIEW.md).

## Requirements

- Python 3.10+ (uses `match` statements and `X | None` type hints)
- No third-party dependencies — standard library only

## Run the REPL

```bash
python3 main.py
```

Type SQL commands at the `db >` prompt, `quit` to exit.

## Run the TCP server

```bash
python3 server.py
```

Starts a TCP server on `127.0.0.1:5432`. Connect with any TCP client, e.g.:

```bash
nc 127.0.0.1 5432
```

Send `quit` to close the connection.

## Run tests

```bash
python3 -m unittest discover -s test -p "*_test.py"
```

Run a single test module, e.g.:

```bash
python3 -m unittest test.binder.binder_test -v
```

## Seed sample data

```bash
python3 scripts/reset_and_seed.py
```

Wipes `test_e2e.db` and recreates + seeds 5 sample tables (`users`, `products`, `orders`, `reviews`, `sessions`) with random data.

## Supported SQL (simplified)

```sql
SELECT col1, col2 | * FROM table [WHERE col = value]
INSERT INTO table VALUES (v1, v2, ...)
CREATE TABLE table (col1 INT, col2 TEXT(size), ...)
DROP TABLE table
UPDATE table SET col = value [WHERE col = value]
DELETE FROM table [WHERE col = value]
```

`WHERE` only supports a single `col = value` equality condition.
