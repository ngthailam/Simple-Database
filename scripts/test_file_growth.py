import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import Engine
from scripts.test_utils import CATEGORIES, ITEMS_SCHEMA

DB_FILE = 'test_file_growth.db'
CYCLES = 10
BATCH_SIZE = 50_000


def row_values(i: int) -> list:
    category = CATEGORIES[i % len(CATEGORIES)]
    active = i % 2
    return [i, f'item{i}', category, i * 3, active]


def report(label: str, engine: Engine) -> None:
    engine.db.flush()
    size_bytes = os.path.getsize(DB_FILE)
    num_pages = engine.db.pager.num_pages
    print(f"{label:<28} file={size_bytes / 1024:9.1f} KiB  pages={num_pages:6d}")


def main():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    engine = Engine(DB_FILE)
    engine.handle_command(f"CREATE TABLE items ({ITEMS_SCHEMA})")
    report("after CREATE TABLE", engine)

    next_id = 1
    for cycle in range(1, CYCLES + 1):
        rows = [row_values(i) for i in range(next_id, next_id + BATCH_SIZE)]
        next_id += BATCH_SIZE
        engine.db.insert_all('items', rows)
        report(f"cycle {cycle}: after insert", engine)

        result = engine.handle_command("DELETE FROM items WHERE active = 1")
        report(f"cycle {cycle}: after delete (~half, {result})", engine)

    print()
    print("Row ids inserted stayed monotonically increasing across cycles (no key reuse),")
    print("so any file/page growth above is purely from orphaned pages left behind by")
    print("insert_all's merge-rebuild and delete's leaf rewrites - a free-list should")
    print("shrink or flatten this curve instead of letting it climb every cycle.")


if __name__ == '__main__':
    main()

# Before re-use page
# after CREATE TABLE           file=     12.0 KiB  pages=     3
# cycle 1: after insert        file=   3200.0 KiB  pages=   800
# cycle 1: after delete (~half, 25000) file=   3200.0 KiB  pages=   800
# cycle 2: after insert        file=   7980.0 KiB  pages=  1995
# cycle 2: after delete (~half, 25000) file=   7980.0 KiB  pages=  1995
# cycle 3: after insert        file=  14352.0 KiB  pages=  3588
# cycle 3: after delete (~half, 25000) file=  14352.0 KiB  pages=  3588
# cycle 4: after insert        file=  22312.0 KiB  pages=  5578
# cycle 4: after delete (~half, 25000) file=  22312.0 KiB  pages=  5578
# cycle 5: after insert        file=  31860.0 KiB  pages=  7965
# cycle 5: after delete (~half, 25000) file=  31860.0 KiB  pages=  7965
# cycle 6: after insert        file=  43000.0 KiB  pages= 10750
# cycle 6: after delete (~half, 25000) file=  43000.0 KiB  pages= 10750
# cycle 7: after insert        file=  55732.0 KiB  pages= 13933
# cycle 7: after delete (~half, 25000) file=  55732.0 KiB  pages= 13933
# cycle 8: after insert        file=  70052.0 KiB  pages= 17513
# cycle 8: after delete (~half, 25000) file=  70052.0 KiB  pages= 17513
# cycle 9: after insert        file=  85964.0 KiB  pages= 21491
# cycle 9: after delete (~half, 25000) file=  85964.0 KiB  pages= 21491
# cycle 10: after insert       file= 103468.0 KiB  pages= 25867
# cycle 10: after delete (~half, 25000) file= 103468.0 KiB  pages= 25867

# After re-use free page
# after CREATE TABLE           file=     12.0 KiB  pages=     3
# cycle 1: after insert        file=   3200.0 KiB  pages=   800
# cycle 1: after delete (~half, 25000) file=   3200.0 KiB  pages=   800
# cycle 2: after insert        file=   7976.0 KiB  pages=  1994
# cycle 2: after delete (~half, 25000) file=   7976.0 KiB  pages=  1994
# cycle 3: after insert        file=  11160.0 KiB  pages=  2790
# cycle 3: after delete (~half, 25000) file=  11160.0 KiB  pages=  2790
# cycle 4: after insert        file=  14340.0 KiB  pages=  3585
# cycle 4: after delete (~half, 25000) file=  14340.0 KiB  pages=  3585
# cycle 5: after insert        file=  17516.0 KiB  pages=  4379
# cycle 5: after delete (~half, 25000) file=  17516.0 KiB  pages=  4379
# cycle 6: after insert        file=  20696.0 KiB  pages=  5174
# cycle 6: after delete (~half, 25000) file=  20696.0 KiB  pages=  5174
# cycle 7: after insert        file=  23880.0 KiB  pages=  5970
# cycle 7: after delete (~half, 25000) file=  23880.0 KiB  pages=  5970
# cycle 8: after insert        file=  27060.0 KiB  pages=  6765
# cycle 8: after delete (~half, 25000) file=  27060.0 KiB  pages=  6765
# cycle 9: after insert        file=  30240.0 KiB  pages=  7560
# cycle 9: after delete (~half, 25000) file=  30240.0 KiB  pages=  7560
# cycle 10: after insert       file=  33424.0 KiB  pages=  8356
# cycle 10: after delete (~half, 25000) file=  33424.0 KiB  pages=  8356