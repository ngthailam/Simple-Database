import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lib.data.pager import Pager
from lib.utils.constants import FREELIST_EMPTY, HEADER_PAGE


class PagerFreelistTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        os.remove(self.db_path)  # Pager creates the file itself
        self.pager = Pager(self.db_path)

    def tearDown(self):
        self.pager.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_fresh_db_has_empty_free_list(self):
        self.assertEqual(self.pager.free_list_head, FREELIST_EMPTY)

    def test_allocate_new_page_grows_file_when_free_list_empty(self):
        before = self.pager.num_pages
        page_num = self.pager.allocate_new_page()
        self.assertEqual(page_num, before)
        self.assertEqual(self.pager.num_pages, before + 1)

    def test_free_then_allocate_reuses_page(self):
        page_num = self.pager.allocate_new_page()
        num_pages_before_free = self.pager.num_pages

        self.pager.free_page(page_num)
        reused = self.pager.allocate_new_page()

        self.assertEqual(reused, page_num)
        self.assertEqual(self.pager.num_pages, num_pages_before_free)  # no growth

    def test_free_list_is_lifo(self):
        a = self.pager.allocate_new_page()
        b = self.pager.allocate_new_page()
        c = self.pager.allocate_new_page()

        self.pager.free_page(a)
        self.pager.free_page(b)
        self.pager.free_page(c)

        # Most recently freed comes back first.
        self.assertEqual(self.pager.allocate_new_page(), c)
        self.assertEqual(self.pager.allocate_new_page(), b)
        self.assertEqual(self.pager.allocate_new_page(), a)

    def test_free_list_exhausted_falls_back_to_growing_file(self):
        page_num = self.pager.allocate_new_page()
        self.pager.free_page(page_num)

        reused = self.pager.allocate_new_page()
        self.assertEqual(reused, page_num)

        num_pages_before = self.pager.num_pages
        fresh = self.pager.allocate_new_page()
        self.assertNotEqual(fresh, page_num)
        self.assertEqual(self.pager.num_pages, num_pages_before + 1)

    def test_free_header_page_raises(self):
        with self.assertRaises(ValueError):
            self.pager.free_page(HEADER_PAGE)

    def test_free_list_head_persists_across_reopen(self):
        a = self.pager.allocate_new_page()
        b = self.pager.allocate_new_page()
        self.pager.free_page(a)
        self.pager.free_page(b)
        self.pager.close()

        reopened = Pager(self.db_path)
        try:
            self.assertEqual(reopened.free_list_head, b)
            self.assertEqual(reopened.allocate_new_page(), b)
            self.assertEqual(reopened.allocate_new_page(), a)
        finally:
            reopened.close()

    def test_corrupt_free_list_head_raises(self):
        # Point the free-list head at a page that was never marked free.
        live_page = self.pager.allocate_new_page()
        self.pager._set_free_list_head(live_page)

        with self.assertRaises(ValueError):
            self.pager.allocate_new_page()


if __name__ == '__main__':
    unittest.main()
