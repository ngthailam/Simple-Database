import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import Engine
from scripts.test_utils import seed_items_table

ROW_COUNT = 1_000_000
GET_ID = 50


def seed(db_file: str) -> Engine:
    return seed_items_table(db_file, ROW_COUNT)


def test_get_by_id():
    print("=== test_get_by_id ===")
    engine = seed('test_get_by_id.db')

    start = time.perf_counter()
    result = engine.handle_command(f"SELECT * FROM items WHERE id = {GET_ID}")
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"SELECT * FROM items WHERE id = {GET_ID} -> ({elapsed_ms:.2f} ms)")
    print(result)

    engine.flush()


def test_get_by_id_missing():
    print("=== test_get_by_id_missing ===")
    engine = seed('test_get_by_id_missing.db')

    missing_id = ROW_COUNT + 1
    start = time.perf_counter()
    result = engine.handle_command(f"SELECT * FROM items WHERE id = {missing_id}")
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"SELECT * FROM items WHERE id = {missing_id} -> ({elapsed_ms:.2f} ms)")
    print(result)

    engine.flush()


def test_get_by_non_key_column():
    print("=== test_get_by_non_key_column (full scan) ===")
    engine = seed('test_get_by_non_key_column.db')

    start = time.perf_counter()
    result = engine.handle_command("SELECT * FROM items WHERE active = 1")
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"SELECT * FROM items WHERE active = 1 -> ({elapsed_ms:.2f} ms, {len(result.splitlines())} lines)")

    engine.flush()


def main():
    test_get_by_id()
    test_get_by_id_missing()
    test_get_by_non_key_column()


if __name__ == '__main__':
    main()
