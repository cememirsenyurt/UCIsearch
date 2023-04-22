from collections import OrderedDict
 
 # Underlying Data Structure is an OrderedDict
class LRUCache:
    def __init__(self, capacity: int):
        self.cache = OrderedDict()
        self.capacity = capacity
    
    # Returns the key if present and moves it to the most recently used
    def get(self, key: int) -> int:
        if key not in self.cache:
            return False
        else:
            self.cache.move_to_end(key)
            return self.cache[key]
    
    # Check if cache is full to remove least recently used
    # Add to cache at most recently used spot
    def put(self, key: int, value: int) -> None:
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last = False)
 
 