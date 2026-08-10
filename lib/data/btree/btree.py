from lib.data.pager import Pager
from lib.data.catalog import TableDef
from typing import Callable
import struct
from lib.utils.constants import *
from lib.data.btree.node import *

class BTree:
    def __init__(self, pager: Pager, table_def: TableDef, value_size: int):
        self.pager = pager
        self.table_def = table_def
        self.header_page = table_def.root_page
        self.value_size = value_size
        
        self.leaf_entry_format = f'<i{value_size}s'
        self.leaf_entry_size = struct.calcsize(self.leaf_entry_format)
        self.leaf_max_keys = (PAGE_SIZE - BNODE_LEAF_HEADER_OFFSET) // self.leaf_entry_size
        
        if self.leaf_entry_size > BNODE_LEAF_VALUE_MAX_BYTES:
            raise ValueError(
                f"row size {self.leaf_entry_size} bytes exceeds max supported {BNODE_LEAF_VALUE_MAX_BYTES} "
                f"bytes (a leaf page must hold at least one row)"
            )
        
        if self.leaf_max_keys < 1:
            raise ValueError(f"computed leaf_max_keys={self.leaf_max_keys}; row size too large for page size {PAGE_SIZE}")

        header_bytes = self.pager.get_page(self.header_page)
        (root_node_page, ) = struct.unpack_from(BTREE_HEADER_FORMAT, header_bytes, 0)
        
        if root_node_page == 0: # Nothing is in this page yet
            self.reset()
        else:
            self.root_node_page = root_node_page
        
    # WRITE(s)
    def write_node(self, page_number: int, node: Node):
        if isinstance(node, LeafNode):
            self._write_leaf_node(page_number, node)
        elif isinstance(node, InternalNode):
            self._write_internal_node(page_number, node)
        else:
            raise ValueError("Invalid node type. Must be LeafNode or InternalNode.")
    
    def _write_leaf_node(self, page_number: int, node: LeafNode):
        is_leaf = 1 # True
        num_keys = len(node.keys)
        next_leaf_number = node.next_leaf_page_num
        
        header_bytes = struct.pack(BNODE_LEAF_HEADER_FORMAT, is_leaf, num_keys, next_leaf_number)
        self.pager.write_bytes(page_number, 0, header_bytes)
        
        offset = BNODE_LEAF_HEADER_OFFSET
        for key, value in zip(node.keys, node.values):
            entry_bytes = struct.pack(self.leaf_entry_format, key, value)
            self.pager.write_bytes(page_number, offset, entry_bytes)
            offset += struct.calcsize(self.leaf_entry_format)
        
    def _write_internal_node(self, page_number: int, node: InternalNode):
        is_leaf = 0
        num_keys = len(node.keys)
        left_most_child_page = node.children[0] if node.children else 0
        
        header_bytes = struct.pack(BNODE_INTERNAL_HEADER_FORMAT, is_leaf, num_keys, left_most_child_page)            
        self.pager.write_bytes(page_number, 0, header_bytes)
        
        offset = BNODE_INTERNAL_HEADER_OFFSET
        for key, child in zip(node.keys, node.children[1:]):
            entry_bytes = struct.pack(BNODE_INTERNAL_ENTRY_FORMAT, key, child)
            self.pager.write_bytes(page_number, offset, entry_bytes)
            offset += struct.calcsize(BNODE_INTERNAL_ENTRY_FORMAT)

    # Read
    def read_node(self, page_number: int) -> Node | None:
        page_bytes = self.pager.get_page(page_number)
        is_leaf = page_bytes[0] == MARKER_TYPE_NODE_LEAF
        is_internal = page_bytes[0] == MARKER_TYPE_NODE_INTERNAL
        
        if is_leaf:
            return self._read_leaf_node(page_number)
        elif is_internal:
            return self._read_internal_node(page_number)
        else:
            return None

    def _read_leaf_node(self, page_number: int) -> LeafNode:
        page_bytes = self.pager.get_page(page_number)

        (is_leaf, key_num, next_leaf_page_number) = struct.unpack_from(BNODE_LEAF_HEADER_FORMAT, page_bytes, 0)

        keys = []
        values = []
        offset = BNODE_LEAF_HEADER_OFFSET
        for _ in range(key_num):
            key, value = struct.unpack_from(self.leaf_entry_format, page_bytes, offset)
            keys.append(key)
            values.append(value)
            offset += struct.calcsize(self.leaf_entry_format)

        return LeafNode(
            keys=keys,
            values=values,
            next_leaf_page_num=next_leaf_page_number
        )

    def _read_internal_node(self, page_number: int) -> InternalNode:
        page_bytes = self.pager.get_page(page_number)

        (is_leaf, key_num, left_most_child_page) = struct.unpack_from(BNODE_INTERNAL_HEADER_FORMAT, page_bytes, 0)

        keys = []
        children = [left_most_child_page]
        offset = BNODE_INTERNAL_HEADER_OFFSET
        for _ in range(key_num):
            key, child_page = struct.unpack_from(BNODE_INTERNAL_ENTRY_FORMAT, page_bytes, offset)
            keys.append(key)
            children.append(child_page)
            offset += struct.calcsize(BNODE_INTERNAL_ENTRY_FORMAT)

        return InternalNode(
            keys=keys,
            children=children
        )

    # Traversal
    def _find_leaf_page(self, key: int) -> int:
        current_page = self.root_node_page

        while True:
            node = self.read_node(current_page)
            if isinstance(node, LeafNode):
                return current_page
            elif isinstance(node, InternalNode):
                child_page = node.children[0]
                for entry_key, entry_child in zip(node.keys, node.children[1:]):
                    if key < entry_key:
                        break
                    child_page = entry_child

                current_page = child_page
            
            else:
                continue    
            
    # Public ops
    def search(self, key: int) -> object | None:
        leaf_page = self._find_leaf_page(key)
        leaf = self._read_leaf_node(leaf_page)
        
        for k, v in zip(leaf.keys, leaf.values):
            if k == key:
                return v
        
        return None
    
    def insert(self, key: int, value: bytes) -> object | None:
        if len(value) > self.leaf_entry_size:
            raise ValueError(f"Value max size is {self.leaf_entry_size}")

        result = self._insert_into_page(page_number=self.root_node_page, key=key, value=value)

        # Node splitting required
        if result is not None:
            (separator_key, new_page_number) = result
            new_root_page = self.pager.allocate_new_page()
            old_root = self.root_node_page
            new_root = InternalNode(keys=[separator_key], children=[old_root, new_page_number])
            self.write_node(new_root_page, new_root)
            self.root_node_page = new_root_page
            self.pager.pack_into(self.header_page, 0, BTREE_HEADER_FORMAT, new_root_page)
        
    # Tuple: @key: int, @value: object. Same key value as insert
    def insert_all(self, items: list[tuple[int, bytes]]):
        if not items:
            # TODO: add something here ? Raise exception
            return
        
        if len(items) < INSERT_ALL_REBUILD_THRESHOLD:
            for key, value in items:
                self.insert(key, value)
            return
        
        # If pass threshold, use another approach that has better performance
        # Connect the leafs in the linked-list, then from that, build the tree from bottom-up
        self._insert_all_merge_rebuilt(items)
        return 
    
    def _insert_all_merge_rebuilt(self, items: list[tuple[int, bytes]]):
        # 1: Validate
        seen_keys = set()
        for key, value in items:
            if len(value) > BNODE_LEAF_VALUE_MAX_BYTES:
                raise ValueError(f"Value max size is {BNODE_LEAF_VALUE_MAX_BYTES}")
            if key in seen_keys:
                raise ValueError(f"Key {key} already exist")
            seen_keys.add(key)
            
        # 2: Sort the batch by key
        data_sorted = sorted(items, key=lambda kv: kv[0])
        
        # 3: Merge new data with existing
        merged_data = self._merge_with_existing(data_sorted)

        # Old tree is fully read into merged_data now - safe to enumerate its
        # pages for freeing, but not to free them yet (new pages aren't
        # written until steps 5/6, and allocate_new_page() could otherwise
        # hand back a page number that's still holding data we haven't
        # finished copying out of).
        old_pages = self._collect_all_pages()

        # 4: Group merged data into leaf-sized chunks (no page numbers yet)
        leaves = self._build_leaf_nodes(merged_data)

        # 5: Allocate pages for each leaf, link next_leaf_page_num, write them
        leaf_pages, leaf_first_keys = self._allocate_and_write_leaves(leaves)

        # 6: Rebuild internal levels bottom-up until a single root page remains
        new_root_page = self._build_internal_levels(leaf_pages, leaf_first_keys)

        # 7: Publish the new root, same as insert()/reset()
        self.root_node_page = new_root_page
        self.pager.pack_into(self.header_page, 0, BTREE_HEADER_FORMAT, new_root_page)

        # 8: Now that the new tree is fully written and published, the old
        # pages are unreachable garbage - reclaim them.
        for page_num in old_pages:
            self.pager.free_page(page_num)

    def _build_internal_levels(self, level_pages: list[int], level_keys: list[int]) -> int:
        # level_pages/level_keys describe one level of the tree: level_pages[i]
        # is a child page, and level_keys[i] is the first key found under it.
        # Loop bottom-up, one level at a time, until only the root remains.
        if len(level_pages) == 1:
            return level_pages[0]

        while len(level_pages) > 1:
            next_level_pages = []
            next_level_keys = []

            children_per_node = INTERNAL_MAX_KEYS + 1
            for start in range(0, len(level_pages), children_per_node):
                chunk_children = level_pages[start:start + children_per_node]
                # keys[i] separates children[i]/children[i+1], so the leftmost
                # child in the chunk contributes no key of its own - matches
                # the InternalNode convention used everywhere else in this file.
                chunk_keys = level_keys[start + 1:start + len(chunk_children)]

                page_number = self.pager.allocate_new_page()
                node = InternalNode(keys=chunk_keys, children=chunk_children)
                self.write_node(page_number, node)

                next_level_pages.append(page_number)
                next_level_keys.append(level_keys[start])

            level_pages = next_level_pages
            level_keys = next_level_keys

        return level_pages[0]

    def _build_leaf_nodes(self, merged_data: list[tuple[int, object]]) -> list[LeafNode]:
        if not merged_data:
            return []

        leaves = []
        current_keys = []
        current_values = []

        for key, value in merged_data:
            if len(current_keys) >= self.leaf_max_keys:
                leaves.append(LeafNode(keys=current_keys, values=current_values))
                current_keys = []
                current_values = []
            current_keys.append(key)
            current_values.append(value)

        leaves.append(LeafNode(keys=current_keys, values=current_values))
        return leaves

    def _allocate_and_write_leaves(self, leaves: list[LeafNode]) -> tuple[list[int], list[int]]:
        leaf_pages = [self.pager.allocate_new_page() for _ in leaves]

        for index, leaf in enumerate(leaves):
            leaf.next_leaf_page_num = leaf_pages[index + 1] if index + 1 < len(leaf_pages) else 0
            self.write_node(leaf_pages[index], leaf)

        leaf_first_keys = [leaf.keys[0] for leaf in leaves]
        return leaf_pages, leaf_first_keys


    def _merge_with_existing(self, data_sorted: list[tuple[int, object]]) -> list[tuple[int, object]]:
        existing_data = list(self.scan())  # already sorted by key

        merged = []
        i, j = 0, 0

        while i < len(existing_data) and j < len(data_sorted):
            existing_key, existing_value = existing_data[i]
            new_key, new_value = data_sorted[j]

            if existing_key < new_key:
                merged.append(existing_data[i])
                i += 1
            elif new_key < existing_key:
                merged.append(data_sorted[j])
                j += 1
            else:
                raise ValueError(f"Key {existing_key} already exist")

        # append whichever side has leftovers
        merged.extend(existing_data[i:])
        merged.extend(data_sorted[j:])

        return merged
                
    
    def _insert_into_page(self, page_number: int, key: int, value: object) -> tuple[int, int] | None:
        node = self.read_node(page_number)
        if isinstance(node, LeafNode):
            return self._insert_leaf_node_into_page(node, page_number, key, value)
        elif isinstance(node, InternalNode):
            return self._insert_internal_node_into_page(node, page_number, key, value)
        else:
            pass
    
    def _insert_leaf_node_into_page(self, node: LeafNode, page_number: int, key: int, value: object):
        keys = node.keys
        values = node.values

        for index, k in enumerate(keys):
            if key < k:
                keys.insert(index, key)
                values.insert(index, value)
                break
            elif key == k:
                raise ValueError(f"Key {key} already exist")
        else:
            keys.append(key)
            values.append(value)
            
            
        if len(keys) <= self.leaf_max_keys:
            updated_node = LeafNode(
                keys=keys,
                values=values,
                next_leaf_page_num=node.next_leaf_page_num
            )
            self._write_leaf_node(page_number=page_number, node=updated_node)
            return None

        # If > self.leaf_max_keys, do split here
        mid = len(keys) // 2

        left_keys, right_keys = keys[:mid], keys[mid:]
        left_values, right_values = values[:mid], values[mid:]

        new_page_number = self.pager.allocate_new_page()

        left_node = LeafNode(
            keys=left_keys,
            values=left_values,
            next_leaf_page_num=new_page_number
        )
        right_node = LeafNode(
            keys=right_keys,
            values=right_values,
            next_leaf_page_num=node.next_leaf_page_num
        )

        self._write_leaf_node(page_number=page_number, node=left_node)
        self._write_leaf_node(page_number=new_page_number, node=right_node)

        separator_key = right_keys[0]
        return (separator_key, new_page_number)        
        
    def _insert_internal_node_into_page(self, node: InternalNode, page_number: int, key: int, value: object) -> tuple[int, int] | None:
        keys = node.keys
        children = node.children

        child_page = children[0]
        for index, entry_key in enumerate(keys):
            if key < entry_key:
                break
            child_page = children[index + 1]

        result = self._insert_into_page(page_number=child_page, key=key, value=value)
        if result is None:
            return None

        separator_key, new_child_page = result

        insert_index = len(keys)
        for index, k in enumerate(keys):
            if separator_key < k:
                insert_index = index
                break

        keys.insert(insert_index, separator_key)
        children.insert(insert_index + 1, new_child_page)

        if len(keys) <= INTERNAL_MAX_KEYS:
            updated_node = InternalNode(keys=keys, children=children)
            self._write_internal_node(page_number=page_number, node=updated_node)
            return None

        mid = len(keys) // 2
        promoted_key = keys[mid]

        left_keys, right_keys = keys[:mid], keys[mid + 1:]
        left_children, right_children = children[:mid + 1], children[mid + 1:]

        new_page_number = self.pager.allocate_new_page()

        left_node = InternalNode(keys=left_keys, children=left_children)
        right_node = InternalNode(keys=right_keys, children=right_children)

        self._write_internal_node(page_number=page_number, node=left_node)
        self._write_internal_node(page_number=new_page_number, node=right_node)

        return (promoted_key, new_page_number)
    
    def delete(self, key: int) -> object | None:
        leaf_page = self._find_leaf_page(key)
        leaf = self._read_leaf_node(leaf_page)

        for index, k in enumerate(leaf.keys):
            if k == key:
                removed_value = leaf.values[index]
                del leaf.keys[index]
                del leaf.values[index]
                self._write_leaf_node(page_number=leaf_page, node=leaf)
                return removed_value

        return None
    
    def delete_where(self, predicate: Callable[[bytes], bool]) -> int:
        delete_count = 0
        for page_number, node in list(self.scan_leaves()):
            # Only handle delete leaf node for now
            if not isinstance(node, LeafNode):
                continue

            new_keys = []
            new_values = []
            changed = False

            for k, v in zip(node.keys, node.values):
                if predicate(v):
                    delete_count += 1
                    changed = True
                else:
                    new_keys.append(k)
                    new_values.append(v)

            if changed:
                updated_node = LeafNode(keys=new_keys, values=new_values, next_leaf_page_num=node.next_leaf_page_num)
                self._write_leaf_node(page_number, updated_node)
                    
        return delete_count
    
    def _collect_all_pages(self) -> list[int]:
        # Full tree traversal (not scan_leaves(), which only follows the leaf
        # linked list) - internal nodes branch, so every child must be visited
        # to enumerate them. Reads only page headers, not full key/value data.
        pages = []
        stack = [self.root_node_page]
        while stack:
            page_num = stack.pop()
            pages.append(page_num)
            node = self.read_node(page_num)
            if isinstance(node, InternalNode):
                stack.extend(node.children)
        return pages

    def delete_all(self) -> int:
        delete_count = 0
        for _, node in self.scan_leaves():
            delete_count += len(node.keys)

        for page_num in self._collect_all_pages():
            self.pager.free_page(page_num)

        self.reset()
        return delete_count

    def scan(self):
        current_page = self.root_node_page
        node = self.read_node(current_page)
        while isinstance(node, InternalNode):
            current_page = node.children[0]
            node = self.read_node(current_page)

        while True:
            for key, value in zip(node.keys, node.values):
                yield key, value

            if node.next_leaf_page_num == 0:
                break
            node = self._read_leaf_node(node.next_leaf_page_num)
            
    def scan_leaves(self):
        current_page = self.root_node_page
        node = self.read_node(current_page)
        
        # Get the first leaf
        while isinstance(node, InternalNode):
            current_page = node.children[0]
            node = self.read_node(current_page)
            
        # Use the linked list in the leaf itself for faster acess, instead of tree traversal
        while True:
            yield current_page, node
            
            if node.next_leaf_page_num == 0:
                break
            
            current_page = node.next_leaf_page_num
            node = self._read_leaf_node(current_page)   
    
    def reset(self):
        root_node_page = self.pager.allocate_new_page()
        initial_node = LeafNode(
            keys=[],
            values=[],
            next_leaf_page_num=0,
        )
        self.write_node(root_node_page, initial_node)
        self.pager.pack_into(self.header_page, 0, BTREE_HEADER_FORMAT, root_node_page)
        self.root_node_page = root_node_page
