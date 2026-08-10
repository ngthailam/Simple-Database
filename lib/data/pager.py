import os
import struct

from lib.utils.constants import HEADER_PAGE, PAGE_SIZE, MAX_PAGES

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
        self.pages: dict[int, bytearray] = {}
        self.dirty: set[int] = set()

    def allocate_new_page(self) -> int:
        page_num = self.num_pages
        self.num_pages += 1
        self.get_page(page_num)  # ensures a blank page is created and cached
        self.dirty.add(page_num)
        return page_num

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
