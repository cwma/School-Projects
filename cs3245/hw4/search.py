#!/usr/bin/env python2.7

"""
Matric: A0112937E
Email:  a0112937@u.nus.edu

This script contains 2 classes.
 - Index is the data structure that encapsulates the process of handling retrieval from the 
   dictionary and postings file
 - PatentSearch is the main class which handlings the process of parsing query from
   the provided query file, executing them and saving the output to file.

PatentSearch implement the Vector Space Model for the searching of documents stored in the 
dictionary and postings file using the SMART notation ddd.qqq of lnc.ltc. In addition,
the search process has 2 steps, the first step performs standard retrieval based on a bag of words
model of features extracted from the query and performs similarity ranking based on lnc.ltc.
The top results are then used to perform query expansion, and the search is re performed with
the new query.

usage is as follows:

$ python search.py -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results

"""
import nltk
import parsers
import cPickle
import argparse
import itertools
from math import log10
from fractions import Fraction
from collections import Counter
from xml.etree import ElementTree
from collections import defaultdict
from nltk.stem.porter import PorterStemmer
import multiprocessing

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
        self.postings_filename = postings_filename
        self.postings_file = open(postings_filename, "rb")

    def _reopen_postings_file(self):
        """
        used for the genetic algorithm.
        a terrible work around to python closing file objects when they're
        passed to child threads/processes.
        """
        self.postings_file = open(self.postings_filename, "rb")

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

    def doc_terms(self, docid):
        """
        returns a list of terms found in a particular docid
        """
        try:
            term_ids = self.index["docs"]["rterms"][docid]
            return map(self.index["lookup"].__getitem__, term_ids)
        except KeyError as error:
            return []

    def doc_ipc(self, docid):
        """
        returns a list of terms found in a particular docid
        """
        try:
            return self.index["docs"]["ipc"][docid]
        except KeyError as error:
            return []

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

class PatentSearch(object):
    """
    This class handles the processing of user queries by searching for relevant documents
    through a vector space model. This process follows the lnc.ltc scheme. A class instance
    is initialized with the provided index and postings filename. Queries are processed through
    a provided query file and results are output into the specified output file. 
    This class implements on top of the vector space model, query expansion, weighted cosine
    similarity based on part of speech tags, and use of top ipc labels to augment weights.
    """

    _DEFAULT_WEIGHT_LABELS = ["VERB", "ADVERB", "NOUN", "ADJECTIVE", "OTHER"]
    _DEFAULT_WEIGHTS = [0.5373928549841915, 0.39612398010335337, 0.0007441924386559651, 0.025509261267636814, 0.04022971120616234]
    #_DEFAULT_WEIGHTS = [0.06851795068509842, 0.03544907940271802, 0.10236917524806412, 0.7270751515003635, -0.06658864316375598]
    #_DEFAULT_WEIGHTS = [0.3053842522494329, -0.04351037104940329, 0.3883340319258735, -0.10825812799526466, 0.1545132167800257]
    #_DEFAULT_WEIGHTS = [1,1,1,1,1]

    _CULL_CUTOFF = 1.5 # cutoff based on average/n 
    _CANDIDATE_CUTOFF = 0.8 # cutoff based on % of top score
    _EXPANSION_LIMIT = 0.05 # limit query expansion to top % terms

    def __init__(self, index_filename, postings_filename):
        """
        index_filename refers to the dictionary file.
        postings_filename refers to the postings file.
        """
        self.weights = {label: weights for label, weights in zip(self._DEFAULT_WEIGHT_LABELS, self._DEFAULT_WEIGHTS)}
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

    def _calculate_similarity(self, query, docs, tagmap, weights=None):
        """
        This method calculates the similarity between a query and a document using their tf.idf values
        according to the lnc.ltc scheme using cosine similarity.  
        Results are returned in a dictionary of docid's mapped to scores.
        If part of speech tagger is available, modify the similarity score for each term based
        on its part of speech tag based on pretrained weights.
        """
        if weights is None:
            weights = self.weights
        results = defaultdict(lambda: 0)
        for docid, doc_terms_weights in docs.items():
            for term, weight in doc_terms_weights.items():
                results[docid] += (query[term] * weight) * (tagmap and weights[tagmap[term]] or 1)
        return results

    def _rank_results(self, results, similarities):
        """
        This method sorts the results with scores in decreasing order, and docid's in increasing order
        for scores that are tied.
        """
        return sorted(results, key=lambda docid: (-similarities[docid], docid))

    def _cull_results(self, similarities):
        """
        culls the results to remove documents that do not meet a cutoff mark.
        """
        average = sum(similarities.values())/len(similarities)
        return filter(lambda docid: similarities[docid] > (average / self._CULL_CUTOFF), similarities.keys())

    def _get_candidates(self, results, similarities):
        """
        retrieves candidates to be used for query expansion.
        """
        top = similarities[results[0]] 
        return filter(lambda docid: similarities[docid] > self._CANDIDATE_CUTOFF * top , results)

    def _execute_query(self, terms, tagmap, modify=None, topk=True):
        """
        This method performs the search of the vector space model using the provided query. 
        Query tf.idf is calculated, and documents containing any of the query terms are retrieved
        and have their tf.idf calculated. Cosine similarity is used to calculated query to document
        similarity, and then the results are ranked. If computing final results dont use topk.
        """
        query_tfidfs = self._calculate_query_tfidf(terms)
        doc_tfidfs = self._retrieve_doc_tfidf(terms)
        similarities = self._calculate_similarity(query_tfidfs, doc_tfidfs, tagmap)
        # modify weights based on ipc labels
        if modify is not None:
            modify(similarities)
        if topk: # dont cull final result
            results = self._cull_results(similarities)
        else:
            results = similarities.keys()
        results = self._rank_results(results, similarities)
        return results, similarities

    def _query_expansion(self, query_filename):
        """
        performs query expansion by performing a search with the original query first,
        followed by aggregating most common terms from the top results and using those
        to augment the original query.
        """
        terms, tagmap = self._parse_query(query_filename)
        preliminary_results, similarities = self._execute_query(terms, tagmap)
        candidates = self._get_candidates(preliminary_results, similarities)
        new_query = []
        for candidate in candidates:
            new_query.extend(self.index.doc_terms(candidate))
        new_terms, new_tagmap = parsers.process_text(new_query, postag=True)
        new_term_counts = Counter(new_terms)
        # get new terms to add to query, but only for the top most common terms found
        new_terms = sorted(set(new_terms), key=lambda term: -new_term_counts[term])[:int(len(new_term_counts)*self._EXPANSION_LIMIT)]
        old_terms = set(terms)
        for term in new_terms:
            if term not in old_terms:
                terms.append(term)
        for key in tagmap:
            if key not in new_tagmap:
                new_tagmap[key] = tagmap[key]
        return terms, new_tagmap

    def _determine_top_groups(self, similarities):
        """
        determines what is most likely the "correct" ipc labels for the query by 
        finding the most present ipc labels in the top results.
        """
        results = sorted(similarities.keys(), key=lambda docid: (-similarities[docid], docid))
        selected_results = self._get_candidates(results, similarities)
        counter = Counter(itertools.chain(*[self.index.doc_ipc(docid) for docid in selected_results]))
        ranked_groups = sorted(counter.keys(), key=counter.__getitem__, reverse=True)
        top = counter[ranked_groups[0]]
        selected_groups = set(filter(lambda ipc: counter[ipc] > top * 0.25, ranked_groups))
        return selected_groups

    def _modify_similarity_score(self, similarities):
        """
        modifies the similarity score for a document if it belongs to the ipc
        group most likely associated with query. Not really useful unless we have
        cut off to increase precision at the cost of recall.
        """
        top_groups = self._determine_top_groups(similarities)
        for docid in similarities.keys():
            if len(set(self.index.doc_ipc(docid)) & top_groups) > 0:
                similarities[docid] *= 1.5

    def _parse_query(self, query_filename):
        """
        Parses the query using the parsers module.
        returns query terms and its associated part of speech
        tags.
        """
        file_tree = ElementTree.parse(query_filename)
        file_root = file_tree.getroot()
        text = file_root[0].text + " " + file_root[1].text
        tokenized_text = parsers.tokenize_text(text)
        terms, tagmap = parsers.process_text(tokenized_text, postag=True)
        return terms, tagmap

    def process_query(self, query_filename, output_filename):
        """
        public method that takes in a query file, processes and executes
        the query, then writes the result to the provided output filename.
        """
        terms, tagmap = self._query_expansion(query_filename)
        results, similarities = self._execute_query(terms, tagmap, modify=self._modify_similarity_score, topk=False)
        try:
            with open(output_filename, 'w') as output_file:
                output_file.write(" ".join(results))
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

    ps = PatentSearch(args.dict, args.postings)
    ps.process_query(args.queries, args.output)