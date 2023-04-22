from Indexer import Indexer
import shelve
from nltk.stem import PorterStemmer
from collections import defaultdict
from LRUCache import LRUCache
import json

INVERTED_INDEX_FILE = './invertedIndex.txt'
BIWORD_INVERTED_INDEX_FILE = './biwordInvertedIndex.txt'

INDEX_TO_INDEX_FILE = './IndexToIndex.shelve'
BIWORD_INDEX_TO_INDEX_FILE = './BiwordIndexToIndex.shelve'

K_THRESHOLD = 150

class Query:
    def __init__(self, indexer: Indexer):
        self.indexer = indexer
        self.index_to_index = shelve.open(INDEX_TO_INDEX_FILE)
        self.biword_index_to_index = shelve.open(BIWORD_INDEX_TO_INDEX_FILE)
        self.biword_inverted_index = open(BIWORD_INVERTED_INDEX_FILE)
        self.inverted_index = open(INVERTED_INDEX_FILE)
        self.cache = LRUCache(capacity=15)

    # Returns a list of Postings
    def getPostings(self, token, query_results, biword=False):
        # Edge case handling
        key = ""
        if len(token) == 0: return []
        elif len(token) == 1: key = token[0]
        elif len(token) > 1: key = token[:2]

        index_to_index = self.index_to_index
        file = self.inverted_index
        if biword:
            index_to_index = self.biword_index_to_index
            file = self.biword_inverted_index

        if key not in index_to_index:
            return

        # If key in index to index search for the postings
        start_index = index_to_index[key]
        file.seek(start_index)

        while True:
            line = file.readline()

            if line == "":
                return

            json_obj = json.loads(line)
            current_word = list(json_obj.keys())[0]
            
            if current_word == token:
                for posting in list(json_obj.values())[0][:K_THRESHOLD]:
                    query_results[posting[0]] += posting[2]
                return

            elif current_word > token:
                return

    def search(self, query_str, useBiword=False):
        if self.cache.get(query_str):
            return self.cache.get(query_str)

        query = query_str.lower().split()
        porter_stem = PorterStemmer()
        query_results = defaultdict(int)

        if len(query) > 1 and useBiword:
            for i in range(len(query) - 1):
                biword_token = f'{porter_stem.stem(query[i])} {porter_stem.stem(query[i+1])}'
                self.getPostings(biword_token, query_results, biword=True)
        
        else:
            for token in query:
                self.getPostings(porter_stem.stem(token), query_results, biword=False)
        
        with shelve.open("./DOCIDtoURL.shelve") as db:
            url_list = [db[id] for id in sorted(list(query_results), key=lambda id: query_results[id], reverse=True)]
            self.cache.put(key=query_str, value=url_list)

        return url_list
