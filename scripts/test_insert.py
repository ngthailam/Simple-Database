import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import Engine

ROW_COUNT = 1_000_000

CATEGORIES = ['electronics', 'books', 'clothing', 'toys']


def row(i: int) -> str:
    category = CATEGORIES[i % len(CATEGORIES)]
    active = i % 2
    return f"({i}, 'item{i}', '{category}', {i * 3}, {active})"

# Baseline: Result: inserting 1,000,000 rows took 84,469.58 ms (~84.5s), averaging 0.0845 ms/row.
def test_insert_one_million():
    print("=== test_insert_one_million ===")
    db_file = 'test_insert.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    engine = Engine(db_file)
    engine.handle_command(
        "CREATE TABLE items (id INT PRIMARY KEY, name TEXT(32), category TEXT(16), score INT, active INT)"
    )

    start = time.perf_counter()
    for i in range(1, ROW_COUNT + 1):
        result = engine.handle_command(f"INSERT INTO items VALUES {row(i)}")
        if 'error' in str(result).lower():
            print(f"error {result}")
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"Inserted {ROW_COUNT} rows in {elapsed_ms:.2f} ms ({elapsed_ms / ROW_COUNT:.4f} ms/row)")

    engine.flush()


def test_insert_one_million_batch():
    print("=== test_insert_one_million_batch ===")
    db_file = 'test_insert_batch.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    engine = Engine(db_file)
    engine.handle_command(
        "CREATE TABLE items (id INT PRIMARY KEY, name TEXT(32), category TEXT(16), score INT, active INT)"
    )

    rows = [
        [i, f'item{i}', CATEGORIES[i % len(CATEGORIES)], i * 3, i % 2]
        for i in range(1, ROW_COUNT + 1)
    ]

    start = time.perf_counter()
    engine.db.insert_all('items', rows)
    engine.db.flush()
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"Inserted {ROW_COUNT} rows via insert_all in {elapsed_ms:.2f} ms ({elapsed_ms / ROW_COUNT:.4f} ms/row)")


def test_insert_four_batches_of_250k():
    print("=== test_insert_four_batches_of_250k ===")
    db_file = 'test_insert_four_batches.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    engine = Engine(db_file)
    engine.handle_command(
        "CREATE TABLE items (id INT PRIMARY KEY, name TEXT(32), category TEXT(16), score INT, active INT)"
    )

    batch_size = 250_000
    total_elapsed_ms = 0.0

    for batch_num in range(4):
        start_id = batch_num * batch_size + 1
        end_id = start_id + batch_size
        rows = [
            [i, f'item{i}', CATEGORIES[i % len(CATEGORIES)], i * 3, i % 2]
            for i in range(start_id, end_id)
        ]

        start = time.perf_counter()
        engine.db.insert_all('items', rows)
        engine.db.flush()
        elapsed_ms = (time.perf_counter() - start) * 1000
        total_elapsed_ms += elapsed_ms

        print(f"Batch {batch_num + 1}/4: inserted {batch_size} rows in {elapsed_ms:.2f} ms ({elapsed_ms / batch_size:.4f} ms/row)")

    print(f"Total: inserted {batch_size * 4} rows across 4 batches in {total_elapsed_ms:.2f} ms ({total_elapsed_ms / (batch_size * 4):.4f} ms/row)")


def main():
    # test_insert_one_million()
    test_insert_one_million_batch()
    test_insert_four_batches_of_250k()


if __name__ == '__main__':
    main()
