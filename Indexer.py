from nltk.tokenize import RegexpTokenizer
from nltk.stem import PorterStemmer
from bs4 import BeautifulSoup
from collections import defaultdict
import shelve
import json
import os.path
import os
import math

'''
Helper Function: Extract Content takes in an array of files and extracts the json in each file.
'''
def extractContent(file):
    with open(file, 'r') as f:
        data = json.loads(f.read())

    return data

'''
Helper Function: getFiles takes in a directory and returns a list of all the files in the directory, and its
subdirectories.
'''
def getFiles(pathToDirectory):
    all_files = []
    for root, dirs, files in os.walk(pathToDirectory):
        for name in files:
            if not name.startswith('.'):
                all_files.append(os.path.join(root, name))
    return all_files

TOTAL_INDEXED_DOCUMENTS = 55393
NUMBER_OF_POSTINGS_TO_DUMP = 1000000
FOLDER_TO_WEBPAGES = './DEV'
FOLDER_TO_PARTIAL_INDICES  = './PartialIndices'
FOLDER_TO_BIWORD_PARTIAL_INDICES = './BiwordPartialIndices'
PATH_TO_SINGLE_PARTIAL_INDICES = './PartialIndices/partialIndex'
PATH_TO_BIWORD_PARTIAL_INDICES = './BiwordPartialIndices/partialIndex'

INVERTED_INDEX_FILE = './invertedIndex.txt'
BIWORD_INVERTED_INDEX_FILE = './biwordInvertedIndex.txt'
INDEX_TO_INDEX_FILE = './IndexToIndex.shelve'
BIWORD_INDEX_TO_INDEX_FILE = './BiwordIndexToIndex.shelve'

class Indexer:
    def __init__(self, FOLDER_TO_WEBPAGES=FOLDER_TO_WEBPAGES, build=False, merge=False):
        # if exists in files, else build it
        if not os.path.exists('./URLtoDOCID.shelve.db') or not os.path.exists('./DOCIDtoURL.shelve.db'):
            self._build_Document_ID_map(getFiles(FOLDER_TO_WEBPAGES))
        self.doc_id_map = shelve.open('./URLtoDOCID.shelve')

        # Creates Folder Directories if not present
        if not os.path.exists(FOLDER_TO_PARTIAL_INDICES):
            os.mkdir(FOLDER_TO_PARTIAL_INDICES)
            build = True
        if not os.path.exists(FOLDER_TO_BIWORD_PARTIAL_INDICES):
            os.mkdir(FOLDER_TO_BIWORD_PARTIAL_INDICES)
            build = True                                         
        if build:
            self._build_partial_indices(getFiles(FOLDER_TO_WEBPAGES))

        if merge or not os.path.exists('./InvertedIndex.txt') or not os.path.exists('./IndexToIndex.shelve.db'):
            self._merge_partial_indices(getFiles(FOLDER_TO_PARTIAL_INDICES), INVERTED_INDEX_FILE, INDEX_TO_INDEX_FILE)
            self._merge_partial_indices(getFiles(FOLDER_TO_BIWORD_PARTIAL_INDICES), BIWORD_INVERTED_INDEX_FILE, BIWORD_INDEX_TO_INDEX_FILE)

        self.index_to_index = shelve.open(INDEX_TO_INDEX_FILE)
        self.biword_index_to_index = shelve.open(BIWORD_INDEX_TO_INDEX_FILE)

    # Destructor used to close shelve files opened in constructor
    def __del__(self):
        self.doc_id_map.close()
        self.index_to_index.close()
        self.biword_index_to_index.close()

    def _build_Document_ID_map(self,files):
        print('Building Document ID HashMap')
        urlTODOCID = {}
        DOCIDTOurl = {}
        for i,file in enumerate(files):
            content = extractContent(file)

            # Gets URL from File if it exists
            try:
                URL = content['url']
            except:
                URL = None

            if URL and URL not in urlTODOCID:
                urlTODOCID[URL] = f'{i}'
                DOCIDTOurl[f'{i}'] = URL


        with shelve.open("./URLtoDOCID.shelve") as db:
            db.update(urlTODOCID)

        with shelve.open("./DOCIDtoURL.shelve") as db:
            db.update(DOCIDTOurl)

    # Helper Method to write in memory inverted index to partial index txt file
    def _write_inverted_index_to_partial_index_file(self, inverted_index, partial_index_counter, path_to_partial_indices):
        with open(f"{path_to_partial_indices}{partial_index_counter}.txt", 'w') as file:
            # add to doc in sorted order for merge algorithm
            for token in sorted(inverted_index):
                # Dump as a json object so its easier to grab and merge later
                token_to_postings = {token: inverted_index[token]}
                file.write(f'{json.dumps(token_to_postings)}\n')

    def _add_to_partial_indice_inverted_index(self, word_occurences, url, inverted_index):
        number_of_postings = 0
        for word, count in word_occurences.items():
            posting = (self.doc_id_map[url], count, None)
            number_of_postings += 1
            if word in inverted_index:
                inverted_index[word].append(posting)
            else:
                inverted_index[word] = [posting]
        return number_of_postings

    def _build_partial_indices(self, files):
        print('Building Partial Indices')
        partial_index_counter = 0
        number_of_postings = 0

        # Used as the in memory dictionary that is dumped to a partialIndex.txt file when filled
        inverted_index = {}
        biword_inverted_index = {}

        for file in files:
            # Used to count word occurences per page
            word_occurences = defaultdict(int)
            biword_occurences = defaultdict(int)

            page_content = extractContent(file)
            url = page_content['url']
            content = page_content['content']

            soup = BeautifulSoup(content, 'html5lib')

            #extract script and style tags from content
            for tag in soup.find_all(['script', 'style']):
                tag.extract()

            #make sure alphanumeric
            tokenizer = RegexpTokenizer(r'[0-9a-zA-Z]+')
            tokens = tokenizer.tokenize(soup.get_text().lower())
            porter_stem = PorterStemmer()
            
            #biword ocurrance and regular word occurance
            for i in range(len(tokens)):
                word_occurences[porter_stem.stem(tokens[i])] += 1
                if i < (len(tokens) - 1):
                    biword_occurences[f"{porter_stem.stem(tokens[i])} {porter_stem.stem(tokens[i+1])}"] += 1
            
            # add the word occurrences to the biword inverted index and single inverted index
            number_of_postings += self._add_to_partial_indice_inverted_index(word_occurences, url, inverted_index)
            self._add_to_partial_indice_inverted_index(biword_occurences, url, biword_inverted_index)

            # This is when we dump our in memory inverted_index to a partial index file.
            if number_of_postings >= NUMBER_OF_POSTINGS_TO_DUMP:
                self._write_inverted_index_to_partial_index_file(inverted_index, partial_index_counter, PATH_TO_SINGLE_PARTIAL_INDICES)
                self._write_inverted_index_to_partial_index_file(biword_inverted_index, partial_index_counter, PATH_TO_BIWORD_PARTIAL_INDICES)

                # increment partial index counter so we write to another partial index
                partial_index_counter += 1

                # Then reset number of postings and inverted index so we can begin filling up in memory inverted index again
                #reseting
                number_of_postings = 0
                inverted_index = {}
                biword_inverted_index= {}

        # Need to dump whatever is left in our inverted index to a partial index file.
        if len(inverted_index) > 0:
            self._write_inverted_index_to_partial_index_file(inverted_index, partial_index_counter, PATH_TO_SINGLE_PARTIAL_INDICES)
            self._write_inverted_index_to_partial_index_file(biword_inverted_index, partial_index_counter, PATH_TO_BIWORD_PARTIAL_INDICES)

    # Computes the tf_idf score for dict we are about to write to file
    def _compute_tf_idf_score(self, lowest_term_dict):
        lowest_term = lowest_term_dict.keys()[0]
        idf = TOTAL_INDEXED_DOCUMENTS / len(lowest_term_dict[lowest_term])
        for posting in lowest_term_dict[lowest_term]:
            tf = posting[1]
            tf_idf = (1 + math.log(tf)) * idf
            posting[2] = tf_idf


    def _merge_partial_indices(self, partial_indice_files, inverted_index_file_path, index_to_index_file_path):
        print('Merging Partial Indices')
        # Used for the merge algorithm, list of file buffers reading the partial indice files
        partial_indice_buffers = [open(file,'r') for file in partial_indice_files]

        # The current token to postings read from each file buffer
        json_objects = {i : json.loads(partial_indice_buffers[i].readline()) for i in range(len(partial_indice_buffers))}

        # The file buffer that is written to, the giant inverted index
        inverted_index = open(inverted_index_file_path, 'w')

        # List of the read buffers that are still not end of file
        remaining_files = [i for i in range(len(partial_indice_buffers))]

        last_token = None
        write_file_seek_index = 0
        index_to_index = {}

        while len(remaining_files) > 0:
            # get lowest_term
            lowest_term = None
            for i in remaining_files:
                # Gets the token from the read buffer file
                term = list(json_objects[i].keys())[0]
                # Need to store the lowest term and its corresponding index
                if lowest_term is None or term < lowest_term:
                    lowest_term = term

            lowest_term_dict = {lowest_term : []}
            # TODO trying this out
            for index in remaining_files:
                token = list(json_objects[index].keys())[0]
                if token == lowest_term:
                    lowest_term_dict[token].extend(json_objects[index][token])

                    next_json_line = partial_indice_buffers[index].readline()

                    if next_json_line == "":
                        remaining_files.remove(index)
                        partial_indice_buffers[index].close()
                    else:
                        json_objects[index] = json.loads(next_json_line)
            
            self._compute_tf_idf_score(lowest_term_dict)
            lowest_term_dict = {lowest_term : sorted(lowest_term_dict[lowest_term], key = lambda x: x[2], reverse=True)}
            lowest_term_string = json.dumps(lowest_term_dict)
            inverted_index.write(f'{lowest_term_string}\n')

            # Check if first char is different to build index to index or if its the first token in indexer
            if write_file_seek_index == 1 and len(last_token) > 0:
                    index_to_index[last_token[0]] = write_file_seek_index

            elif not last_token or (len(last_token) > 1 and len(lowest_term) > 1) and (last_token[0:2] != lowest_term[0:2]):
                index_to_index[lowest_term[0:2]] = write_file_seek_index

            elif not last_token or (len(last_token) > 0 and len(lowest_term) > 0) and (last_token[0] != lowest_term[0]):
                index_to_index[lowest_term[0]] = write_file_seek_index

            write_file_seek_index += len(lowest_term_string) + 1
            last_token = lowest_term

        inverted_index.close()
        with shelve.open(index_to_index_file_path) as db:
            db.update(index_to_index)

if __name__ == '__main__':
    Indexer(build=True,merge=True)
