import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import Engine

ROW_COUNT = 1_000_000
DELETE_ID = 50

CATEGORIES = ['electronics', 'books', 'clothing', 'toys']


def row(i: int) -> str:
    category = CATEGORIES[i % len(CATEGORIES)]
    active = i % 2
    return f"({i}, 'item{i}', '{category}', {i * 3}, {active})"


def seed(db_file: str) -> Engine:
    if os.path.exists(db_file):
        os.remove(db_file)

    engine = Engine(db_file)
    engine.handle_command(
        "CREATE TABLE items (id INT PRIMARY KEY, name TEXT(32), category TEXT(16), score INT, active INT)"
    )

    for i in range(1, ROW_COUNT + 1):
        result = engine.handle_command(f"INSERT INTO items VALUES {row(i)}")
        if 'error' in str(result).lower():
            print(f"INSERT INTO items VALUES {row(i)} -> {result}")

    return engine


def test_delete_by_id():
    print("=== test_delete_by_id ===")
    engine = seed('test_delete_by_id.db')

    start = time.perf_counter()
    result = engine.handle_command(f"DELETE FROM items WHERE id = {DELETE_ID}")
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"DELETE FROM items WHERE id = {DELETE_ID} -> {result} ({elapsed_ms:.2f} ms)")

    engine.flush()


def test_delete_where_active():
    print("=== test_delete_where_active ===")
    engine = seed('test_delete_where_active.db')

    start = time.perf_counter()
    result = engine.handle_command("DELETE FROM items WHERE active = 1")
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"DELETE FROM items WHERE active = 1 -> {result} ({elapsed_ms:.2f} ms)")

    engine.flush()


def test_delete_all():
    print("=== test_delete_all ===")
    engine = seed('test_delete_all.db')

    start = time.perf_counter()
    result = engine.handle_command("DELETE FROM items")
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"DELETE FROM items -> {result} ({elapsed_ms:.2f} ms)")

    engine.flush()


def main():
    test_delete_by_id()
    test_delete_where_active()
    test_delete_all()


if __name__ == '__main__':
    main()
