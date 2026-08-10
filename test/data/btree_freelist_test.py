import math
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lib.data.btree.btree import BTree
from lib.data.catalog import TableDef
from lib.data.pager import Pager
from lib.utils.constants import (
    FREELIST_EMPTY,
    FREELIST_PAGE_HEADER_FORMAT,
    INSERT_ALL_REBUILD_THRESHOLD,
    INTERNAL_MAX_KEYS,
)

VALUE_SIZE = 4  # values are just a packed 4-byte int, keeps leaves small enough to span multiple pages


def pack_value(i: int) -> bytes:
    return struct.pack('<i', i)


def unpack_value(value: bytes) -> int:
    return struct.unpack('<i', value)[0]


class BTreeFreelistTestBase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        os.remove(self.db_path)  # Pager creates the file itself

        self.pager = Pager(self.db_path)
        root_page = self.pager.allocate_new_page()
        table_def = TableDef(name='t', root_page=root_page, columns=[])
        self.btree = BTree(self.pager, table_def, VALUE_SIZE)

    def tearDown(self):
        self.pager.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _items(self, keys) -> list:
        return [(k, pack_value(k)) for k in keys]

    def _scanned_keys(self) -> list:
        return [key for key, _ in self.btree.scan()]

    def _pages_needed_for(self, num_keys: int) -> int:
        # Mirrors _insert_all_merge_rebuilt's page layout exactly: ceil(n /
        # leaf_max_keys) leaves, then bottom-up internal levels at ceil(n /
        # (INTERNAL_MAX_KEYS + 1)) each, until a single root page remains.
        level_size = math.ceil(num_keys / self.btree.leaf_max_keys)
        total = level_size
        while level_size > 1:
            level_size = math.ceil(level_size / (INTERNAL_MAX_KEYS + 1))
            total += level_size
        return total


class InsertAllTest(BTreeFreelistTestBase):
    def test_small_batch_below_threshold(self):
        items = self._items(range(1, 51))
        self.btree.insert_all(items)
        self.assertEqual(self._scanned_keys(), list(range(1, 51)))

    def test_empty_batch_is_noop(self):
        self.btree.insert_all([])
        self.assertEqual(self._scanned_keys(), [])

    def test_duplicate_key_within_batch_raises(self):
        with self.assertRaises(ValueError):
            self.btree.insert_all(self._items([1, 2, 2, 3]))

    def test_duplicate_key_against_existing_raises(self):
        self.btree.insert_all(self._items([1, 2, 3]))
        with self.assertRaises(ValueError):
            self.btree.insert_all(self._items([3, 4]))

    def test_merge_rebuild_path_spans_multiple_leaves(self):
        # Large enough batch to trigger the merge-rebuild path (as opposed
        # to the one-by-one insert() loop) and to span multiple leaf pages.
        keys = range(1, INSERT_ALL_REBUILD_THRESHOLD + 1)
        self.btree.insert_all(self._items(keys))
        self.assertEqual(self._scanned_keys(), list(keys))

    def test_merge_rebuild_merges_with_existing_data(self):
        self.btree.insert_all(self._items(range(1, INSERT_ALL_REBUILD_THRESHOLD + 1)))
        self.btree.insert_all(self._items(range(INSERT_ALL_REBUILD_THRESHOLD + 1, 2 * INSERT_ALL_REBUILD_THRESHOLD + 1)))

        self.assertEqual(self._scanned_keys(), list(range(1, 2 * INSERT_ALL_REBUILD_THRESHOLD + 1)))

    def test_merge_rebuild_frees_old_pages_instead_of_leaking(self):
        keys = range(1, INSERT_ALL_REBUILD_THRESHOLD + 1)
        self.btree.insert_all(self._items(keys))
        pages_after_first_rebuild = self.pager.num_pages

        # A second rebuild over roughly the same amount of data should reuse
        # the pages orphaned by the first rebuild rather than doubling the
        # page count - old pages must have been freed, not leaked.
        more_keys = range(INSERT_ALL_REBUILD_THRESHOLD + 1, 2 * INSERT_ALL_REBUILD_THRESHOLD + 1)
        self.btree.insert_all(self._items(more_keys))
        pages_after_second_rebuild = self.pager.num_pages

        growth = pages_after_second_rebuild - pages_after_first_rebuild

        # Exact expected growth: the second rebuild allocates a fresh
        # P(2*THRESHOLD)-page tree before freeing the old one (see
        # _insert_all_merge_rebuilt step 8), reusing the single page freed by
        # the first rebuild's leftover empty root along the way. If old pages
        # leaked instead, growth would be P(2*THRESHOLD) pages higher still
        # (the old THRESHOLD-sized tree retained on top).
        expected_growth = self._pages_needed_for(2 * INSERT_ALL_REBUILD_THRESHOLD) - 1
        self.assertEqual(growth, expected_growth)
        self.assertNotEqual(self.pager.free_list_head, FREELIST_EMPTY)


class DeleteAllTest(BTreeFreelistTestBase):
    def test_delete_all_empty_table_returns_zero(self):
        self.assertEqual(self.btree.delete_all(), 0)
        self.assertEqual(self._scanned_keys(), [])

    def test_delete_all_returns_row_count_and_empties_tree(self):
        keys = range(1, INSERT_ALL_REBUILD_THRESHOLD + 1)
        self.btree.insert_all(self._items(keys))

        deleted = self.btree.delete_all()

        self.assertEqual(deleted, len(list(keys)))
        self.assertEqual(self._scanned_keys(), [])

    def test_delete_all_leaves_tree_usable_afterwards(self):
        self.btree.insert_all(self._items(range(1, INSERT_ALL_REBUILD_THRESHOLD + 1)))
        self.btree.delete_all()

        # Root must be a valid, readable node - not a page freed out from
        # under the tree - and further inserts must work correctly.
        self.btree.insert_all(self._items(range(1, 11)))
        self.assertEqual(self._scanned_keys(), list(range(1, 11)))

    def test_delete_all_frees_pages_for_reuse(self):
        keys = range(1, INSERT_ALL_REBUILD_THRESHOLD + 1)
        self.btree.insert_all(self._items(keys))
        pages_before_delete = self.pager.num_pages

        self.btree.delete_all()
        self.assertNotEqual(self.pager.free_list_head, FREELIST_EMPTY)

        # Re-inserting a similarly sized batch should mostly reuse freed
        # pages rather than growing the file back to (or past) its old size.
        self.btree.insert_all(self._items(keys))
        pages_after_reinsert = self.pager.num_pages

        self.assertLess(pages_after_reinsert, pages_before_delete + 5)

    def test_delete_all_frees_internal_nodes_too(self):
        # With INSERT_ALL_REBUILD_THRESHOLD rows the tree has at least one
        # internal level; _collect_all_pages must walk internal nodes (not
        # just scan_leaves()'s linked list) for delete_all to fully reclaim.
        self.btree.insert_all(self._items(range(1, INSERT_ALL_REBUILD_THRESHOLD + 1)))
        all_pages_before = set(self.btree._collect_all_pages())
        self.assertGreater(len(all_pages_before), 1)  # sanity: more than just a lone leaf/root

        self.btree.delete_all()

        # Every old page (leaves and internal nodes alike) must have passed
        # through the free list. reset() immediately reallocates one of them
        # as the fresh empty root, so it's no longer on the list by the time
        # we check - exclude the current root and require everything else.
        freed = set()
        head = self.pager.free_list_head
        while head != FREELIST_EMPTY:
            freed.add(head)
            page_bytes = self.pager.get_page(head)
            _marker, head = struct.unpack_from(FREELIST_PAGE_HEADER_FORMAT, page_bytes, 0)
        still_unaccounted = all_pages_before - freed - {self.btree.root_node_page}
        self.assertEqual(still_unaccounted, set())


if __name__ == '__main__':
    unittest.main()
