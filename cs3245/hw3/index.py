#!/usr/bin/env python2.7

"""
Matric: A0112937E
Email:  a0112937@u.nus.edu

This script contains 3 functions.
index_files takes in path to train files and outputs an intermediate index and postings dictionary
write_postings writes the posting file and updates the index with postings address pointers
write_index writes the finalized index file

Usage is as follows:

$ python index.py -i directory-of-documents -d dictionary-file -p postings-file

"""
import os
import nltk
import cPickle
import argparse
import itertools
from math import log10
from collections import Counter
from collections import defaultdict
from nltk.stem.porter import PorterStemmer

def index_files(path_name):
    """
    This method takes in a file directory path and indexes every file found in that directory's level.
    Text is tokenized using nltk's sent_tokenize and word_tokenize, and PorterStemmer for stemming
    Outputs an index dictionary containing term to document frequency mappings
    as well as a posting index containing term to postings mappings and term frequencies for each document.
    Temporarily store a sorted list of all postings in the index.
    """
    stemmer = PorterStemmer()
    index = defaultdict(lambda: {"dfreq": 0})
    length = {}
    postings = defaultdict(lambda: {"docid": [], "tfreq": []})
    files = sorted(os.listdir(path_name), key=int)
    for file_name in files:
        with open(os.path.join(path_name, file_name), 'r') as text_file:
            sentences = nltk.sent_tokenize(text_file.read())
        text_file.close()
        # lowercases all sentences, process them into individual terms using word_tokenize, before stemming 
        all_tokens = map(stemmer.stem_word, itertools.chain(*map(nltk.word_tokenize, map(str.lower, sentences))))
        counter = Counter(all_tokens)
        # level 2 normalized document length
        length[file_name] = sum(map(lambda x: ((1 + log10(int(x))) * 1)**2 , counter.values())) ** 0.5
        # store term frequency as its tfidf lnc score
        for term in counter:
            lnc_score = ((1 + log10(counter[term])) * 1) / length[file_name]
            postings[term]["tfreq"].append(lnc_score)
        # append docid's in same order as term frequencies 
        token_set = set(all_tokens)
        for term in token_set:
            index[term]["dfreq"] += 1
            postings[term]["docid"].append(file_name)

    index = {"terms": dict(index), "length": length, "total_doc": len(files)}
    return index, postings

def write_postings(index, postings, postings_filename):
    """
    This method takes in the index and postings dictionary, writes the postings to the provided
    postings filename, and updates the index with the postings address pointer. The term frequencies
    are stored in the line after the postings list in the same order of document id's.
    """
    with open(postings_filename, "w") as postings_file:
        for term in postings.keys():
            index["terms"][term]["docid"] = postings_file.tell()
            docids = " ".join(postings[term]["docid"]) + "\n"
            postings_file.write(docids)
            index["terms"][term]["tfreq"] = postings_file.tell()
            tfreq = " ".join(map(str, postings[term]["tfreq"])) + "\n"
            postings_file.write(tfreq)
    postings_file.close()

def write_index(index, index_filename):
    """This method writes the index dictionary to the provided filename"""
    with open(index_filename, 'wb') as dict_file:
        cPickle.dump(index, dict_file)
    dict_file.close()

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    # mandatory arguments
    parser.add_argument("-i", required=True, help="directory-of-documents", metavar="train", dest="train")
    parser.add_argument("-d", required=True, help="dictionary-file", metavar="dict", dest="dict")
    parser.add_argument("-p", required=True, help="postings-file", metavar="postings", dest="postings")

    args = parser.parse_args()
    index, postings = index_files(args.train)

    write_postings(index, postings, args.postings)
    write_index(index, args.dict)
