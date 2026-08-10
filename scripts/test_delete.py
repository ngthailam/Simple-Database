import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import Engine
from scripts.test_utils import seed_items_table

ROW_COUNT = 1_000_000
DELETE_ID = 50


def seed(db_file: str) -> Engine:
    return seed_items_table(db_file, ROW_COUNT)


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
