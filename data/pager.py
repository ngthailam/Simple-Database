import os

PAGE_SIZE = 4096 # 4KB
MAX_PAGES = 100

# This is for the concept of dividing database (file) into pages
# Each page is 4KB to match (1) Filesystem block size and (2) OS virtual memory page size

class Pager:
    def __init__(self, filename: str):
        self.filename = filename
        if not os.path.exists(filename):
            open(filename, 'wb').close()
        self.file = open(filename, 'r+b')
        self.file_length = os.path.getsize(filename)
        # @key: page index
        # @value: bytes value
        self.pages: dict[int, bytearray] = {}
        
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

    def flush_all(self):
        for page_num in self.pages:
            self.flush(page_num)

    def close(self):
        self.flush_all()
        self.file.close()

if __name__ == '__main__':
    pager = Pager('test_pages.db')

    page0 = pager.get_page(0)
    page0[0:5] = b'hello'   # mutate bytes directly within the page

    page1 = pager.get_page(1)
    page1[0:5] = b'world'

    pager.close()  # writes both pages back to disk

    # reopen and verify persistence
    pager2 = Pager('test_pages.db')
    print(pager2.get_page(0)[0:5])  # b'hello'
    print(pager2.get_page(1)[0:5])  # b'world'
    pager2.close()
