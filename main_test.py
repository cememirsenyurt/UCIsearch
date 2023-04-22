from Indexer import Indexer
from nltk.tokenize import RegexpTokenizer
from Query import Query
from bs4 import BeautifulSoup
import shelve
import time
from Indexer import getFiles, extractContent
def main():
    i = Indexer()
    q = Query(i)
    start = time.time()
    print(q.search("master of software engineering")[:5])
    end = time.time()
    print((end-start)*1000)
    print("-----------")
    start = time.time()
    print(q.search("master of software engineering")[:5])
    end = time.time()
    print((end-start)*1000)

    
    '''
    with shelve.open('DOCIDtoURL.shelve') as db:
        print(db['19309'])
    '''
if __name__ == '__main__':
    main()