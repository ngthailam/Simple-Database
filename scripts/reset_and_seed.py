import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import Engine, DB_FILE

USER_COUNT = 300_000
REVIEW_COUNT = 65_521
PRODUCT_COUNT = 250_000

FIRST_NAMES = ['alice', 'bob', 'carol', 'dave', 'erin', 'frank', 'grace', 'heidi', 'ivan', 'judy']

TABLES = [
    {
        'name': 'users',
        'schema': 'id INT PRIMARY KEY, username TEXT(32), email TEXT(255), age INT, active INT',
        'row_count': USER_COUNT,
        'row': lambda i: (
            f"({i}, '{FIRST_NAMES[i % len(FIRST_NAMES)]}{i}', "
            f"'{FIRST_NAMES[i % len(FIRST_NAMES)]}{i}@example.com', "
            f"{random.randint(18, 80)}, {random.randint(0, 1)})"
        ),
    },
    {
        'name': 'products',
        'schema': 'id INT PRIMARY KEY, name TEXT(64), price INT, stock INT, category TEXT(32), sku TEXT(16), weight INT, in_stock INT',
        'row_count': PRODUCT_COUNT,
        'row': lambda i: (
            f"({i}, 'product{i}', {random.randint(100, 10000)}, {random.randint(0, 500)}, "
            f"'category{i % 10}', 'SKU{i:05d}', {random.randint(1, 5000)}, {random.randint(0, 1)})"
        ),
    },
    {
        'name': 'orders',
        'schema': 'id INT PRIMARY KEY, user_id INT, product_id INT',
        'row_count': USER_COUNT + PRODUCT_COUNT,
        'row': lambda i: f"({i}, {random.randint(1, USER_COUNT)}, {random.randint(1, PRODUCT_COUNT)})",
    },
    {
        'name': 'reviews',
        'schema': 'id INT PRIMARY KEY, product_id INT, rating INT',
        'row_count': REVIEW_COUNT,
        'row': lambda i: f"({i}, {random.randint(1, PRODUCT_COUNT)}, {random.randint(1, 5)})",
    },
    {
        'name': 'sessions',
        'schema': 'id INT PRIMARY KEY, user_id INT, token TEXT(64)',
        'row_count': USER_COUNT,
        'row': lambda i: f"({i}, {random.randint(1, USER_COUNT)}, 'token{i}')",
    },
]


def main():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"deleted {DB_FILE}")

    engine = Engine()

    total_start = time.perf_counter()

    for table in TABLES:
        result = engine.handle_command(f"CREATE TABLE {table['name']} ({table['schema']})")
        print(f"CREATE TABLE {table['name']} -> {result}")

        table_start = time.perf_counter()
        for i in range(1, table['row_count'] + 1):
            values = table['row'](i)
            result = engine.handle_command(f"INSERT INTO {table['name']} VALUES {values}")
            if 'error' in str(result).lower():
                print(f"INSERT INTO {table['name']} VALUES {values} -> {result}")
        table_elapsed = time.perf_counter() - table_start

        print(f"seeded {table['row_count']} rows into {table['name']} ({table_elapsed:.3f}s, "
              f"{table_elapsed / table['row_count'] * 1000:.3f} ms/row)")

    engine.flush()
    total_elapsed = time.perf_counter() - total_start
    print(f"done seeding {DB_FILE} ({total_elapsed:.3f}s total)")


if __name__ == '__main__':
    main()
