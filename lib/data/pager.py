import os
import struct

from lib.utils.constants import *

# This is for the concept of dividing database (file) into pages
# Each page is 4KB to match (1) Filesystem block size and (2) OS virtual memory page size

class Pager:
    def __init__(self, filename: str):
        self.filename = filename
        if not os.path.exists(filename):
            open(filename, 'wb').close()
        self.file = open(filename, 'r+b')
        self.file_length = os.path.getsize(filename)
        self.num_pages = max(1, self.file_length // PAGE_SIZE)  # page 0 always reserved

        # Init helpers (must exist before get_page is called below)
        self.pages: dict[int, bytearray] = {}
        self.dirty: set[int] = set()

        header_page_bytes = self.get_page(HEADER_PAGE)
        free_list_head, = struct.unpack_from(PAGER_FREELIST_HEAD_FORMAT, header_page_bytes, PAGER_FREELIST_HEAD_OFFSET)
        if free_list_head == 0:  # zero-filled page (brand-new DB): not yet initialized
            free_list_head = FREELIST_EMPTY
            struct.pack_into(PAGER_FREELIST_HEAD_FORMAT, header_page_bytes, PAGER_FREELIST_HEAD_OFFSET, free_list_head)
        self.free_list_head = free_list_head

    def allocate_new_page(self) -> int:
        # Re-use free page if possible
        if self.free_list_head != FREELIST_EMPTY:
            current_free_page_num = self.free_list_head
            page_bytes = self.get_page(current_free_page_num)
            page_type, next_free_page_num = struct.unpack_from(FREELIST_PAGE_HEADER_FORMAT, page_bytes, 0)
            if page_type != MARKER_TYPE_FREE_PAGE:
                raise ValueError(f"page {current_free_page_num} is on the free-list but is not marked as free (corrupt free-list)")

            self._set_free_list_head(next_free_page_num)
            self.dirty.add(current_free_page_num)
            return current_free_page_num

        # Allocate entirely new page
        page_num = self.num_pages
        self.num_pages += 1
        self.get_page(page_num)  # ensures a blank page is created and cached
        self.dirty.add(page_num)
        return page_num

    # Mark a page as a free page
    def free_page(self, page_num: int) -> None:
        # Disallow freeing the header page
        if page_num == HEADER_PAGE:
            raise ValueError("Cannot free the header page")

        page_bytes = self.get_page(page_num)
        struct.pack_into(FREELIST_PAGE_HEADER_FORMAT, page_bytes, 0, MARKER_TYPE_FREE_PAGE, self.free_list_head)
        self.dirty.add(page_num)

        self._set_free_list_head(page_num)

    def _set_free_list_head(self, page_num: int) -> None:
        self.free_list_head = page_num
        header_page_bytes = self.get_page(HEADER_PAGE)
        struct.pack_into(PAGER_FREELIST_HEAD_FORMAT, header_page_bytes, PAGER_FREELIST_HEAD_OFFSET, page_num)
        self.dirty.add(HEADER_PAGE)

    def write_bytes(self, page_num: int, offset: int, data: bytes):
        page = self.get_page(page_num)
        page[offset:offset + len(data)] = data
        self.dirty.add(page_num)

    def pack_into(self, page_num: int, offset: int, fmt: str, *args):
        page = self.get_page(page_num)
        struct.pack_into(fmt, page, offset, *args)
        self.dirty.add(page_num)

    def get_page(self, page_num: int) -> bytearray:
        if page_num > MAX_PAGES:
            raise ValueError(f"page number out of bounds: {page_num}")
        
        if page_num not in self.pages:
            num_pages_on_disk = self.file_length # Since page size is fixed, file length == num of total pages

            if page_num < num_pages_on_disk: # Page already exist in disk
                self.file.seek(page_num * PAGE_SIZE)
                data = self.file.read(PAGE_SIZE)
                page = bytearray(data)
                
                if len(page) < PAGE_SIZE: # If somehow page is smaller than PAGE_SIZE, pad zeros
                    remaining = PAGE_SIZE - len(page)
                    page.extend(b'\x00' * remaining)

            else: # Need allocate new
                page = bytearray(PAGE_SIZE) # all zeros
            self.pages[page_num] = page
            

        return self.pages[page_num]
    
    def flush(self, page_num: int):
        if page_num not in self.pages:
            return

        self.file.seek(page_num * PAGE_SIZE)
        self.file.write(self.pages[page_num])
        self.file.flush()
        self.file_length = max(self.file_length, (page_num + 1) * PAGE_SIZE)
        self.dirty.discard(page_num)

    def flush_all(self):
        for page_num in list(self.dirty):
            self.flush(page_num)

    def close(self):
        self.flush_all()
        self.file.close()
