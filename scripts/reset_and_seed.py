import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import Engine, DB_FILE

FIRST_NAMES = ['alice', 'bob', 'carol', 'dave', 'erin', 'frank', 'grace', 'heidi', 'ivan', 'judy']

TABLES = [
    {
        'name': 'users',
        'schema': 'id INT, username TEXT(32), email TEXT(255), age INT, active INT',
        'row_count': 300,
        'row': lambda i: (
            f"({i}, '{FIRST_NAMES[i % len(FIRST_NAMES)]}{i}', "
            f"'{FIRST_NAMES[i % len(FIRST_NAMES)]}{i}@example.com', "
            f"{random.randint(18, 80)}, {random.randint(0, 1)})"
        ),
    },
    {
        'name': 'products',
        'schema': 'id INT, name TEXT(64), price INT, stock INT, category TEXT(32), sku TEXT(16), weight INT, in_stock INT',
        'row_count': 250,
        'row': lambda i: (
            f"({i}, 'product{i}', {random.randint(100, 10000)}, {random.randint(0, 500)}, "
            f"'category{i % 10}', 'SKU{i:05d}', {random.randint(1, 5000)}, {random.randint(0, 1)})"
        ),
    },
    {
        'name': 'orders',
        'schema': 'id INT, user_id INT, product_id INT',
        'row_count': 350,
        'row': lambda i: f"({i}, {random.randint(1, 300)}, {random.randint(1, 250)})",
    },
    {
        'name': 'reviews',
        'schema': 'id INT, product_id INT, rating INT',
        'row_count': 275,
        'row': lambda i: f"({i}, {random.randint(1, 250)}, {random.randint(1, 5)})",
    },
    {
        'name': 'sessions',
        'schema': 'id INT, user_id INT, token TEXT(64)',
        'row_count': 320,
        'row': lambda i: f"({i}, {random.randint(1, 300)}, 'token{i}')",
    },
]


def main():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"deleted {DB_FILE}")

    engine = Engine()

    for table in TABLES:
        result = engine.handle_command(f"CREATE TABLE {table['name']} ({table['schema']})")
        print(f"CREATE TABLE {table['name']} -> {result}")

        for i in range(1, table['row_count'] + 1):
            values = table['row'](i)
            result = engine.handle_command(f"INSERT INTO {table['name']} VALUES {values}")
            if 'error' in str(result).lower():
                print(f"INSERT INTO {table['name']} VALUES {values} -> {result}")

        print(f"seeded {table['row_count']} rows into {table['name']}")

    engine.flush()
    print(f"done seeding {DB_FILE}")


if __name__ == '__main__':
    main()
