from __future__ import annotations

class Node:
    pass

class LeafNode(Node):
    def __init__(self, keys: list[int], values: list[object], next_leaf_page_num: int = 0):
        self.keys = keys
        self.values = values
        self.next_leaf_page_num = next_leaf_page_num

class InternalNode(Node):
    def __init__(self, keys: list[int], children: list[int]):
        self.keys = keys
        self.children = children
