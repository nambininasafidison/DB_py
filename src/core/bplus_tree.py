class BPlusTree:
    def __init__(self, order=3):
        self.order = order
        self.root = BPlusTreeNode(order, is_leaf=True)

    def insert(self, key, value):
        split_node = self.root.insert(key, value)
        if split_node:
            new_root = BPlusTreeNode(self.order, is_leaf=False)
            new_root.keys = [split_node.keys[0]]
            new_root.children = [self.root, split_node]
            self.root = new_root

    def search(self, key):
        return self.root.search(key)

class BPlusTreeNode:
    def __init__(self, order, is_leaf=False):
        self.order = order
        self.is_leaf = is_leaf
        self.keys = []
        self.values = [] if is_leaf else None
        self.children = [] if not is_leaf else None
        self.next = None

    def insert(self, key, value):
        if self.is_leaf:
            idx = 0
            while idx < len(self.keys) and self.keys[idx] < key:
                idx += 1
            self.keys.insert(idx, key)
            self.values.insert(idx, value)
            if len(self.keys) > self.order:
                return self.split()
        else:
            idx = 0
            while idx < len(self.keys) and key > self.keys[idx]:
                idx += 1
            child = self.children[idx]
            split_node = child.insert(key, value)
            if split_node:
                mid_key = split_node.keys[0]
                self.keys.insert(idx, mid_key)
                self.children.insert(idx + 1, split_node)
                if len(self.keys) > self.order:
                    return self.split()
        return None

    def split(self):
        mid = len(self.keys) // 2
        new_node = BPlusTreeNode(self.order, is_leaf=self.is_leaf)
        new_node.keys = self.keys[mid:]
        if self.is_leaf:
            new_node.values = self.values[mid:]
            new_node.next = self.next
            self.next = new_node
            self.keys = self.keys[:mid]
            self.values = self.values[:mid]
        else:
            new_node.children = self.children[mid:]
            self.keys = self.keys[:mid]
            self.children = self.children[:mid]
        return new_node

    def search(self, key):
        if self.is_leaf:
            return [self.values[i] for i, k in enumerate(self.keys) if k == key]
        else:
            idx = 0
            while idx < len(self.keys) and key > self.keys[idx]:
                idx += 1
            return self.children[idx].search(key)