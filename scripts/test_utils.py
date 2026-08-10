import os

from engine import Engine

CATEGORIES = ['electronics', 'books', 'clothing', 'toys']

ITEMS_SCHEMA = 'id INT PRIMARY KEY, name TEXT(32), category TEXT(16), score INT, active INT'


def item_row_values(i: int) -> list:
    category = CATEGORIES[i % len(CATEGORIES)]
    active = i % 2
    return [i, f'item{i}', category, i * 3, active]


def seed_table_batch(engine: Engine, table_name: str, row_count: int, row_values_fn) -> None:
    rows = [row_values_fn(i) for i in range(1, row_count + 1)]
    engine.db.insert_all(table_name, rows)
    engine.db.flush()


def seed_items_table(db_file: str, row_count: int) -> Engine:
    if os.path.exists(db_file):
        os.remove(db_file)

    engine = Engine(db_file)
    engine.handle_command(f"CREATE TABLE items ({ITEMS_SCHEMA})")

    seed_table_batch(engine, 'items', row_count, item_row_values)

    return engine
