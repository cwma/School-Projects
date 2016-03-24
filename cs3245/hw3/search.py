#!/usr/bin/env python2.7

"""
Matric: A0112937E
Email:  a0112937@u.nus.edu

This script contains 2 classes.
 - Index is the data structure that encapsulates the process of handling retrieval from the 
   dictionary and postings file
 - VSSearch is the main class which handlings the process of parsing queries from
   the provided query file, executing them and saving the output to file.

These implement the Vector Space Model for the searching of documents stored in the 
dictionary and postings file using the SMART notation ddd.qqq of lnc.ltc

usage is as follows:

$ python search.py -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results

"""
import nltk
import cPickle
import argparse
from math import log10
from fractions import Fraction
from collections import Counter
from collections import defaultdict
from nltk.stem.porter import PorterStemmer

class Index(object):
    """
    This class encapsulates the process of accessing the dictionary, as well as accessing
    the postings list and term frequencies on demand using address pointers stored in the dictionary. Upon initialization
    it marshalls the dictionary file into a dictionary object, and keeps a file pointer to the postings
    file open.
    """

    def __init__(self, index_filename, postings_filename):
        """
        index_filename refers to the dictionary file.
        postings_filename refers to the postings file.
        """
        self._load_index(index_filename)
        self.total_docs = self.index["total_doc"]
        self.postings_file = open(postings_filename, "rb")

    def _load_index(self, index_filename):
        """
        loads the dictionary from file into a dictionary data structure.
        """
        with open(index_filename,'rb') as dict_file:
            self.index = cPickle.load(dict_file)
        dict_file.close()

    def _read_postings_file(self, address):
        """
        Takes in the address for an entry in the postings file and returns it.
        """
        self.postings_file.seek(address)
        return self.postings_file.readline()

    def docfreq(self, term):
        """
        returns the document frequency of a term.
        """
        try:
            return self.index["terms"][term]["dfreq"]
        except KeyError as error:
            return 0

    def doclength(self, docid):
        """
        returns the level 2 normalized length of a document.
        """
        try:
            return self.index["length"][docid]
        except KeyError as error:
            return 0

    def postings(self, term):
        """
        returns a list of tuples of the docid and term frequencies for a term 
        """
        try:
            postings = self._read_postings_file(self.index["terms"][term]["docid"]).split()
            termfreqs = self._read_postings_file(self.index["terms"][term]["tfreq"]).split()
        except KeyError as error:
            return []
        else:
            return zip(postings, termfreqs)

class VSSearch(object):
    """
    This class handles the processing of user queries by searching for relevant documents
    through a vector space model. This process follows the lnc.ltc scheme. A class instance
    is initialized with the provided index and postings filename. Queries are processed through
    a provided query file and results are output into the specified output file. 
    """

    k = 10

    def __init__(self, index_filename, postings_filename):
        """
        index_filename refers to the dictionary file.
        postings_filename refers to the postings file.
        """
        self.stemmer = PorterStemmer()
        self.index = Index(index_filename, postings_filename)

    def _calculate_query_tfidf(self, terms):
        """
        This method converts a list of query terms into a vector representing its cosine normalized
        tf.idf values following the ltc scheme, and returns a map of term to tf.idf value.
        """
        counter = Counter(terms)
        idf = lambda freq: freq > 0 and (log10(Fraction(self.index.total_docs, freq))) or 0
        q_wts = [((1 + log10(counter[term])) * idf(self.index.docfreq(term))) for term in counter.keys()]
        length = sum(map(lambda x: x**2, q_wts)) ** 0.5
        return length > 0 and {term: wts for term, wts in zip(terms, map(lambda x: x / length, q_wts))} or {}

    def _retrieve_doc_tfidf(self, terms):
        """
        This method retrieves all the docid's and term frequencies stored as tf.idf values 
         following the lnc scheme, and returns a dictionary of tf.idf values mapped
        to a term mapped to its document. {"docid": {"term": tf.idf}} This allows for ease of similarity 
        evaluation.
        """
        doc_wts = defaultdict(lambda: {})
        for term, postings in zip(terms, map(self.index.postings, set(terms))):
            for docid, tfreq in postings:
                doc_wts[docid][term] = float(tfreq)
        return doc_wts

    def _calculate_similarity(self, query, docs):
        """
        This method calculates the similarity between a query and a document using their tf.idf values
        according to the lnc.ltc scheme using cosine similarity.  
        Results are returned in a dictionary of docid's mapped to scores.
        """
        results = defaultdict(lambda: 0)
        for docid, doc_terms_weights in docs.items():
            for term, weight in doc_terms_weights.items():
                results[docid] += query[term] * weight
        return results

    def _rank_results(self, results):
        """
        This method sorts the results with scores in decreasing order, and docid's in increasing order
        for scores that are tied.
        """
        return sorted(results.keys(), key=lambda docid: (-results[docid], int(docid)))

    def _execute_query(self, query):
        """
        This method performs the search of the vector space model using the provided query.
        Query tf.idf is calculated, and documents containing any of the query terms are retrieved
        and have their tf.idf calculated. Cosine similarity is used to calculated query to document
        similarity, and then the results are ranked, with the top 10 being returned.
        """
        terms = [self.stemmer.stem(term) for term in nltk.word_tokenize(query.lower())]
        query_tfidfs = self._calculate_query_tfidf(terms)
        doc_tfidfs = self._retrieve_doc_tfidf(terms)
        results = self._calculate_similarity(query_tfidfs, doc_tfidfs)
        ranked_results = self._rank_results(results)
        try:
            return ranked_results[:self.k] 
        except IndexError as error:
            return ranked_results

    def process_queries(self, query_filename, output_filename):
        """
        This method takes in a query filename and output filename.
        For every query, it writes the output into a new line.
        """
        try:
            with open(query_filename, 'r') as query_file, open(output_filename, 'w') as output_file:
                for row in query_file:
                    result = self._execute_query(row)
                    output_file.write(" ".join(result) + "\n")
        except IOError as error:
            print "IO Error occured while attempting to run BooleanSearch"
            sys.exit(error.args[1])

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    # mandatory arguments
    parser.add_argument("-d", required=True, help="dictionary-file", metavar="dict", dest="dict")
    parser.add_argument("-p", required=True, help="postings-file", metavar="postings", dest="postings")
    parser.add_argument("-q", required=True, help="file-of-queries", metavar="queries", dest="queries")
    parser.add_argument("-o", required=True, help="output-file-of-results", metavar="output", dest="output")

    args = parser.parse_args()

    vs = VSSearch(args.dict, args.postings)
    vs.process_queries(args.queries, args.output)