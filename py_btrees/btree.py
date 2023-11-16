import bisect
import sys
import os
sys.path.append(os.path.abspath('.'))
from typing import Any, List, Optional, Tuple, Union, Dict, Generic, TypeVar, cast, NewType
from py_btrees.disk import DISK, Address
from py_btrees.btree_node import BTreeNode, KT, VT, get_node

"""
----------------------- Starter code for your B-Tree -----------------------

Helpful Tips (You will need these):
1. Your tree should be composed of BTreeNode objects, where each node has:
    - the disk block address of its parent node
    - the disk block addresses of its children nodes (if non-leaf)
    - the data items inside (if leaf)
    - a flag indicating whether it is a leaf

------------- THE ONLY DATA STORED IN THE `BTree` OBJECT SHOULD BE THE `M` & `L` VALUES AND THE ADDRESS OF THE ROOT NODE -------------
-------------              THIS IS BECAUSE THE POINT IS TO STORE THE ENTIRE TREE ON DISK AT ALL TIMES                    -------------

2. Create helper methods:
    - get a node's parent with DISK.read(parent_address)
    - get a node's children with DISK.read(child_address)
    - write a node back to disk with DISK.write(self)
    - check the health of your tree (makes debugging a piece of cake)
        - go through the entire tree recursively and check that children point to their parents, etc.
        - now call this method after every insertion in your testing and you will find out where things are going wrong
3. Don't fall for these common bugs:
    - Forgetting to update a node's parent address when its parent splits
        - Remember that when a node splits, some of its children no longer have the same parent
    - Forgetting that the leaf and the root are edge cases
    - FORGETTING TO WRITE BACK TO THE DISK AFTER MODIFYING / CREATING A NODE
    - Forgetting to test odd / even M values
    - Forgetting to update the KEYS of a node who just gained a child
    - Forgetting to redistribute keys or children of a node who just split
    - Nesting nodes inside of each other instead of using disk addresses to reference them
        - This may seem to work but will fail our grader's stress tests
4. USE THE DEBUGGER
5. USE ASSERT STATEMENTS AS MUCH AS POSSIBLE
    - e.g. `assert node.parent != None or node == self.root` <- if this fails, something is very wrong

--------------------------- BEST OF LUCK ---------------------------
"""

# Complete both the find and insert methods to earn full credit
class BTree:
    def __init__(self, M: int, L: int):
        """
        Initialize a new BTree.
        You do not need to edit this method, nor should you.
        """
        self.root_addr: Address = DISK.new() # Remember, this is the ADDRESS of the root node
        # DO NOT RENAME THE ROOT MEMBER -- LEAVE IT AS self.root_addr
        DISK.write(self.root_addr, BTreeNode(self.root_addr, None, None, True))
        self.M = M # M will fall in the range 2 to 99999
        self.L = L # L will fall in the range 1 to 99999
        
    def _create_new_root(self, old_root: BTreeNode, median_key: KT, new_node_addr: Address) -> None:
        """_summary_

        Args:
            old_root (BTreeNode): _description_
            median_key (KT): _description_
            new_node_addr (Address): _description_

        Returns:
            _type_: _description_
        """
        new_root_addr = DISK.new()
        new_root = BTreeNode(new_root_addr, None, None, False)
        new_root.keys = [median_key]
        new_root.children_addrs = [old_root.my_addr, new_node_addr]

        old_root.parent_addr = new_root.my_addr
        new_node = get_node(new_node_addr)
        new_node.parent_addr = new_root.my_addr

        new_root.write_back()
        old_root.write_back()
        new_node.write_back()

        self.root_addr = new_root.my_addr
        
        return None
        
    def _insert_into_parent(self, parent: BTreeNode, median_key: KT, new_node_addr: Address) -> None:
        """_summary_

        Args:
            parent (BTreeNode): _description_
            median_key (KT): _description_
            new_node_addr (Address): _description_

        Returns:
            _type_: _description_
        """
        idx = parent.find_idx(median_key)
        parent.keys.insert(idx, median_key)
        parent.children_addrs.insert(idx + 1, new_node_addr)

        if len(parent.keys) > self.M:
            self._split_node(parent)
        else:
            parent.write_back()
        
        return None
    
    def _split_node(self, node: BTreeNode) -> None:
        """_summary_

        Args:
            node (BTreeNode): _description_

        Returns:
            _type_: _description_
        """
        median_idx = len(node.keys) // 2
        median_key = node.keys[median_idx]

        new_node_addr = DISK.new()
        new_node = BTreeNode(new_node_addr, node.parent_addr, None, node.is_leaf)
        new_node.keys = node.keys[median_idx + 1:]
        new_node.data = node.data[median_idx + 1:] if node.is_leaf else []
        new_node.children_addrs = node.children_addrs[median_idx + 1:] if not node.is_leaf else []

        node.keys = node.keys[:median_idx]
        node.data = node.data[:median_idx] if node.is_leaf else []
        node.children_addrs = node.children_addrs[:median_idx + 1] if not node.is_leaf else []

        # # Before we write back the nodes, let's update the parent and children relationships
        # if node.parent_addr is not None:
        #     # If there's a parent, we need to update it with the median key and new node address
        #     parent_node = get_node(node.parent_addr)
        #     insert_position = parent_node.find_idx(median_key)

        #     # Insert the median key and new node address into the parent node
        #     parent_node.keys.insert(insert_position, median_key)
        #     parent_node.children_addrs.insert(insert_position + 1, new_node_addr)

        #     # Now we need to update the index_in_parent for the new node
        #     new_node.index_in_parent = insert_position + 1

        #     # We also need to update the index_in_parent for all children to the right of the new node
        #     for i in range(new_node.index_in_parent + 1, len(parent_node.children_addrs)):
        #         child_node = get_node(parent_node.children_addrs[i])
        #         child_node.index_in_parent = i
        #         child_node.write_back()

        #     # If the parent is now overfull, it needs to be split
        #     if len(parent_node.keys) > self.M:
        #         self._split_node(parent_node)
        #     else:
        #         # Otherwise, we can just write back the updated parent node
        #         parent_node.write_back()

        # else:
        #     # If there's no parent, this is the root and we need to create a new root
        #     self._create_new_root(node, median_key, new_node_addr)

        # Finally, we write back the split node and the new node
        node.write_back()
        new_node.write_back()

        if node.parent_addr is not None:
            parent_node = get_node(node.parent_addr)
            self._insert_into_parent(parent_node, median_key, new_node_addr)
        else:
            self._create_new_root(node, median_key, new_node_addr)
        
        return None
        
    def _find_leaf_node_for_key(self, key: KT) -> BTreeNode:
        """_summary_

        Args:
            key (KT): _description_

        Returns:
            BTreeNode: _description_
        """
        current_node = get_node(self.root_addr)
        while not current_node.is_leaf:
            child_idx = current_node.find_idx(key)
            if child_idx > 0 and current_node.keys[child_idx - 1] == key:
                child_idx -= 1
            child_addr = current_node.children_addrs[child_idx]
            current_node = get_node(child_addr)
            
        return current_node

    def insert(self, key: KT, value: VT) -> None:
        """
        Insert the key-value pair into your tree.
        It will probably be useful to have an internal
        _find_node() method that searches for the node
        that should be our parent (or finds the leaf
        if the key is already present).

        Overwrite old values if the key exists in the BTree.

        Make sure to write back all changes to the disk!
        """
        # Step 1: Locate the appropriate leaf node for the key
        leaf_node = self._find_leaf_node_for_key(key)

        # Step 2: Insert the key-value pair into the leaf node
        leaf_node.insert_data(key, value)

        # Step 3: Check for overflow and split if necessary
        if len(leaf_node.keys) > self.L:
            self._split_node(leaf_node)

        # Step 4: Write the modified leaf node back to the disk
        leaf_node.write_back()
        
        return None

    def find(self, key: KT) -> Optional[VT]:
        """
        Find a key and return the value associated with it.
        If it is not in the BTree, return None.

        This should be implemented with a logarithmic search
        in the node.keys array, not a linear search. Look at the
        BTreeNode.find_idx() method for an example of using
        the builtin bisect library to search for a number in 
        a sorted array in logarithmic time.
        """
        current_node = get_node(self.root_addr) # Start from the root node
        
        # Loop until a leaf node is reached
        while not current_node.is_leaf:
            # Find the child index where the key fits in
            idx = current_node.find_idx(key)
            if idx < len(current_node.keys) and current_node.keys[idx] == key:
                # The key is equal to a key in the node, so we take the left child
                idx += 1
            current_node = current_node.get_child(idx)
        
        # Now current_node is the leaf node where the key would be if it exists
        return current_node.find_data(key)

if __name__ == "__main__":
    btree = BTree(M=4, L=3)  # For example, let's take M=4, L=3
    # Insert some key-value pairs to test
    btree.insert(10, "value10")
    btree.insert(20, "value20")
    btree.insert(50, "value50")
    btree.insert(15, "value15")
    btree.insert(20, "value20 (overwrite)")
    print("Insert complete.")
    keys = [10, 20, 50, 15, 25, 5]
    for key in keys:
        value = btree.find(key)
        print(f"Key {key} has value:", value)
    
    print("Find complete.")