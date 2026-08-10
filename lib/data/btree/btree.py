from lib.data.pager import Pager
from lib.data.catalog import TableDef
import struct
from lib.utils.constants import *
from lib.data.btree.node import *

class BTree:
    def __init__(self, pager: Pager, table_def: TableDef):
        self.pager = pager
        self.table_def = table_def
        self.header_page = table_def.root_page
        
        header_bytes = self.pager.get_page(self.header_page)
        (root_node_page, ) = struct.unpack_from(BTREE_HEADER_FORMAT, header_bytes, 0)
        
        if root_node_page == 0: # Nothing is in this page yet
            root_node_page = self.pager.allocate_new_page()
            initial_node = LeafNode(
                keys=[],
                values=[],
                next_leaf_page_num=0,
            )
            self.write_node(root_node_page, initial_node)
            self.pager.pack_into(self.header_page, 0, BTREE_HEADER_FORMAT, root_node_page)
        
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
            entry_bytes = struct.pack(BNODE_LEAF_ENTRY_FORMAT, key, value)
            self.pager.write_bytes(page_number, offset, entry_bytes)
            offset += struct.calcsize(BNODE_LEAF_ENTRY_FORMAT)
        
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
    def read_node(self, page_number: int) -> Node:
        page_bytes = self.pager.get_page(page_number)
        is_leaf = page_bytes[0] == 1
        is_internal = page_bytes[0] == 0
        
        if is_leaf:
            return self._read_leaf_node(page_number)
        elif is_internal:
            return self._read_internal_node(page_number)
        else:
            raise ValueError("Invalid node type. Must be LeafNode or InternalNode.")

    def _read_leaf_node(self, page_number: int) -> LeafNode:
        page_bytes = self.pager.get_page(page_number)

        (is_leaf, key_num, next_leaf_page_number) = struct.unpack_from(BNODE_LEAF_HEADER_FORMAT, page_bytes, 0)

        keys = []
        values = []
        offset = BNODE_LEAF_HEADER_OFFSET
        for _ in range(key_num):
            key, value = struct.unpack_from(BNODE_LEAF_ENTRY_FORMAT, page_bytes, offset)
            keys.append(key)
            values.append(value)
            offset += struct.calcsize(BNODE_LEAF_ENTRY_FORMAT)

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
    
    def insert(self, key: int, value: object) -> object | None:
        if len(value) > BNODE_LEAF_VALUE_MAX_BYTES:
            raise ValueError(f"Value max size is {BNODE_LEAF_VALUE_MAX_BYTES}")

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
        
    
    def _insert_into_page(self, page_number: int, key: int, value: object) -> tuple[int, int] | None:
        node = self.read_node(page_number)
        if isinstance(node, LeafNode):
            return self._insert_leaf_node_into_page(node, page_number, key, value)
        else:
            return self._insert_internal_node_into_page(node, page_number, key, value)
    
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
            
            
        if len(keys) <= LEAF_MAX_KEYS:
            updated_node = LeafNode(
                keys=keys,
                values=values,
                next_leaf_page_num=node.next_leaf_page_num
            )
            self._write_leaf_node(page_number=page_number, node=updated_node)
            return None

        # If > LEAF_MAX_KEYS, do split here
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
