#!/usr/bin/env python2.7

"""
Matric: A0112937E
Email:  a0112937@u.nus.edu

This script contains 2 classes and 2 helper methods.
 - CorpusParser is a multiprocessing worker class that handles the parsing of individual 
   files that it receives from a queue that is filled by the CorpusIndexer instance.
   It returns the results into a result queue which the CorpusIndexer then consumes.
   It is the consumer in a consumer/producer pattern.
 - CorpusIndexer is the main management class that handles the worker processes. Once
   the worker processes have processed the input files into suitable data structures, it
   will perform post processing of the results so that they can be appropriatedly serialized
   It is the producer in a consumer/producer pattern.

Usage is as follows:

$ python index.py -i directory-of-documents -d dictionary-file -p postings-file

"""
import os
import nltk
import parsers
import cPickle
import argparse
import itertools
import multiprocessing
from math import log10
from collections import Counter
from collections import defaultdict      

class CorpusParser(multiprocessing.Process):
    """
    A multiprocessing worker class that consumes work from CorpusIndexer.
    The queue it consumes from is expected to contain a tuple of the
    file name and full file path of the corpus files to be indexed.
    """

    def __init__(self, event, tasks, results, ipc):
        """ipc refers to the index of ipc labels to a bag of words description that label"""
        multiprocessing.Process.__init__(self)
        self._event = event
        self._tasks = tasks
        self._results = results
        self._ipc = ipc
        self.daemon = True

    def _process_task(self, file_name, full_file_path):
        """
        The main method that handles the processing of the corpus files.
        Uses the methods from the parsers module to parse the corpus file,
        tokenize and process text into proper terms, expand the document, using
        the ipc descriptions, and computes the lnc score.
        """
        file_name = file_name.split('.')[0]
        raw_terms, terms, ipc_list = parsers.parse_corpus_xml(full_file_path)
        terms = parsers.expand_terms(self._ipc, terms, ipc_list)
        counter = Counter(terms)
        lnc_scores = {}
        # level 2 normalized document length
        length = sum(map(lambda x: ((1 + log10(int(x))) * 1)**2 , counter.values())) ** 0.5
        for term in counter:
            lnc_scores[term]  = ((1 + log10(counter[term])) * 1) / length
        return (file_name, counter, lnc_scores, raw_terms, ipc_list)

    def run(self):
        """run method for CorpusParser worker process"""
        while self._event.is_set():
            task = self._tasks.get()
            result = self._process_task(*task)
            self._results.put(result)
            self._tasks.task_done()

class CorpusIndexer():
    """
    Class that manages the CorpusParser worker instances, and consumes
    the result and performs post-processing so that they can be
    serialized into the dictionary and postings file.
    """

    _NUM_WORKERS = multiprocessing.cpu_count()

    def __init__(self):
        """init"""
        self._event = multiprocessing.Event()
        self._tasks = multiprocessing.JoinableQueue()

    def _load_ipc(self):
        """
        loads the IPC file. The IPC file is a preprocessed dictionary
        of IPC scheme titles mapped to terms associated with that labels description.
        original file was obtained from:
        http://www.wipo.int/ipc/itos4ipc/ITSupport_and_download_area/20160101/IPC_scheme_title_list/EN_ipc_title_list_20160101.zip
        """
        with open("IPC.txt",'rb') as dict_file:
            self._ipc = cPickle.load(dict_file)
        dict_file.close()

    def _start_workers(self):
        """
        Starts the worker processes.
        """
        self._load_ipc()
        self._event.set()
        self._workers = [CorpusParser(self._event, self._tasks, self._results, self._ipc) for x in xrange(self._NUM_WORKERS)]
        [worker.start() for worker in self._workers]

    def _process_result(self, file_name, counter, lnc_scores, raw_terms, ipc_list):
        """
        takes the result from the SearchWorkers, and adds them into
        a dictionary appropriately formatted to be later serialized.
        """
        for term in counter:
            self.index[term]["dfreq"] += 1
            self.postings[term]["tfreq"].append(lnc_scores[term])
            self.postings[term]["docid"].append(file_name)
        for term in raw_terms:
            if term not in self.lookup:
                self.lookup[len(self.lookup)] = term
            self.docs[file_name].append(len(self.lookup))
        [self.docsipc[file_name].append(ipc[1]) for ipc in ipc_list]

    def index_files(self, path_name):
        """
        Indexes all the corpus files in the provided path.
        returns a dictionary and postings dictionary variables.
        """
        self._results = multiprocessing.Queue()
        self._start_workers()
        self.index = defaultdict(lambda: {"dfreq": 0})
        self.docsipc = defaultdict(lambda: [])
        self.docs = defaultdict(lambda: [])
        self.lookup = {}
        self.length = {}
        self.postings = defaultdict(lambda: {"docid": [], "tfreq": []})
        files = sorted(os.listdir(path_name))
        for file_name in files:
            full_file_path = os.path.join(path_name, file_name)
            self._tasks.put((file_name, full_file_path))
        self._tasks.join()
        self._event.clear()
        while not self._results.empty():
            result = self._results.get()
            self._process_result(*result)
        final_index = {"terms": dict(self.index), "total_doc": len(files), "lookup": self.lookup, "docs": { "rterms": dict(self.docs), "ipc": dict(self.docsipc)} }
        return final_index, self.postings

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
    ci = CorpusIndexer()
    index, postings = ci.index_files(args.train)

    write_postings(index, postings, args.postings)
    write_index(index, args.dict)
