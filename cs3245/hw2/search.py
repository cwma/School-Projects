#!/usr/bin/env python2.7

"""
Matric: A0112937E
Email:  a0112937@u.nus.edu

This script contains 3 classes:
 - SkipList is a data structure that has pointers that skip every |size**0.5| entries.
 - Index is the data structure that encapsulates the process of handling retrieval from the 
   dictionary and postings file.
 - BooleanSearch is the main class which handlings the process of parsing queries from
   the provided query file, executing them and saving the output to file.

Usage is as follows:

$ python search.py -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results

"""
import cPickle
import argparse
from math import floor
from nltk.stem.porter import PorterStemmer

class SkipList(object):
    """
    SkipList is a data structure that is used to represent a skip list using python's built in list object.
    Upon initialization it takes in a pointer to an instance of the Index class. This is used to compute
    NOT (invert) queries. The decision to reference the index instance in every SkipList is for the facilitation
    of handling the SkipList objects by overriding python's bitwise operators for the relevant operations. 
    The array argument is to initialize a SkipList with an existing list or if none is provided an empty list.
    As this is implemented over pythons list, skip pointers are simulated through arithmatic calculations based
    on index position. For all intents and purposes the result is the same as a linked list with skip pointers.
    SkipList is treated as an immutable object.

    """

    def __init__(self, index, array=[]):
        """
        index is a required argument that references an Index class instance.
        array is an optional argument where an existing list can be provided otherwise
        create a new empty instance.
        As an immutable object, the length of the list is fixed and its length is stored
        in a variable. This is to save on excessive len() function calls.

        """
        self._pointer = 0
        self.array = array
        self.index = index
        self.list_size = len(self.array)
        self._skip_size = int(floor(self.list_size ** 0.5))
        self._list_size_offset = self.list_size - (1 + self._skip_size)

    def __len__(self):
        return self.list_size

    def __str__(self):
        return " ".join(map(str, self.array))

    def __repr__(self):
        return self.array.__repr__()

    def next(self):
        """iterator like method to move to the next item in list if it exists"""
        self._pointer += 1

    def peek(self):
        """retrieves the next item in list if it exists, else return current, without moving the pointer"""
        try:
            return self.array[self._pointer + 1]
        except IndexError as ie:
            return None

    def current(self):
        """returns the current item based on pointer location"""
        try:
            return self.array[self._pointer]
        except IndexError as ie:
            return None

    def has_skip(self):
        """checks if the pointer is on an index value that allows for a skip"""
        return (self._pointer % self._skip_size == 0) and (self._pointer <= self._list_size_offset)

    def skip(self):
        """if a skip is available, move the pointer to the skip target index"""
        self._pointer += self._skip_size

    def skip_peek(self):
        """retrieves the next skip item in list if it exists, else return current, without moving the pointer"""
        try:
            return self.array[self._pointer + self._skip_size]
        except IndexError as ie:
            return None

    def __and__(self, skiplist2):
        """
        This method overloads the & bitwise operator for the SkipList object.
        The & operation is treated as a Boolean AND operation for all elements in this objects list
        and the provided second skiplist, or otherwise known as an intersection operation.
        """
        result = []
        self_current, skiplist2_current = self.current(), skiplist2.current()
        while self_current is not None and skiplist2_current is not None:
            if self_current == skiplist2_current:
                result.append(self_current)
                if self.has_skip() and skiplist2.peek() >= self.skip_peek():
                    self.skip()
                    skiplist2.next()
                elif skiplist2.has_skip() and self.peek() >= skiplist2.skip_peek():
                    skiplist2.skip()
                    self.next()
                else:
                    self.next()
                    skiplist2.next()
            elif self_current < skiplist2_current:
                if self.has_skip() and self.skip_peek() <= skiplist2_current:
                    self.skip()
                else:
                    self.next()
            else:
                if skiplist2.has_skip() and skiplist2.skip_peek() <= self_current:
                    skiplist2.skip()
                else:
                    skiplist2.next()
            self_current, skiplist2_current = self.current(), skiplist2.current()
        return SkipList(self.index, result)

    def __sub__(self, skiplist2):
        """
        This method overloads the - operator for the SkipList object.
        The - operation is treated as a Boolean AND NOT operation, removing elements from this list
        which are in the second skiplist, or otherwise known as a difference operation.
        """
        result = []
        self_current, skiplist2_current = self.current(), skiplist2.current()
        while self_current is not None and skiplist2_current is not None:
            if self_current == skiplist2_current:
                self.next()
                skiplist2.next()
            elif self_current < skiplist2_current:
                result.append(self_current)
                self.next()
            else:
                if skiplist2.has_skip() and skiplist2.skip_peek() <= self_current:
                    skiplist2.skip()
                else:
                    skiplist2.next()
            self_current, skiplist2_current = self.current(), skiplist2.current()
        map(result.append, self.array[self._pointer:])
        return SkipList(self.index, result)

    def __or__(self, skiplist2):
        """
        This method overloads the | operator for the SkipList object.
        The | operation is treated as a Boolean OR operation, keeping unique elements from this list
        and the second list, or otherwise known as a union operation.
        """
        self_set = set(self.array)
        skiplist2_set = set(skiplist2.array)
        result = sorted(list(self_set | skiplist2_set), key=int)

        # as pythons c based sets are substantially faster, and skiplists have no benefits for unions,
        # the following code is depreciated and fallback to using python sets for or operations
        """
        result = []
        self_current, skiplist2_current = self.current(), skiplist2.current()
        while self_current is not None and skiplist2_current is not None:
            if self_current == skiplist2_current:
                result.append(self_current)
                self.next()
                skiplist2.next()
            elif self_current < skiplist2_current:
                result.append(self_current)
                self.next()
            else:
                result.append(skiplist2_current)
                skiplist2.next()
            self_current, skiplist2_current = self.current(), skiplist2.current()
        map(result.append, self.array[self._pointer:])
        map(result.append, self.skiplist2[skiplist2._pointer:])
        """
        return SkipList(self.index, result)

    def __invert__(self):
        """
        This method overloads the ~ bitwise operator for the SkipList object.
        The ~ operation is treated as a Boolean NOT operation, using the master postings list
        from the index as a universal set, which inverts the current set. 
        Effectively it is the difference between all elements and this objects elements.
        """
        return self.index.get_all_postings() - self

class Index(object):
    """
    This class encapsulates the process of accessing the dictionary, as well as accessing
    the postings list on demand using address pointers stored in the dictionary. Upon initialization
    it marshalls the dictionary file into a dictionary object, and keeps a file pointer to the postings
    file open.
    """

    def __init__(self, index_filename, postings_filename):
        """
        index_filename refers to the dictionary file.
        postings_filename refers to the postings file.
        """
        self._load_index(index_filename)
        self.postings_file = open(postings_filename, "rb")

    def __getitem__(self, term):
        """
        returns a SkipList object containing a list of postings for the provided term.
        postings is retrieved from file on demand.
        """
        try:
            postings_str = self._read_postings_file(self.index["terms"][term]["posting"])
        except KeyError as error:
            return SkipList(self, [])
        else:
            return SkipList(self, map(int, postings_str.split()))

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

    def get_freq(self, term):
        """
        returns the frequency of a term in the dictionary.
        """
        return self.index["terms"][term]["freq"]

    def get_postings(self, term):
        return self[term]

    def get_all_postings(self):
        """
        returns a SkipList object containing the master list of postings.
        retrieved from file on demand.
        """
        postings = self._read_postings_file(self.index["all_postings"])
        return SkipList(self, map(int, postings.split()))

class BooleanSearch(object):
    """
    This class handles the parsing and execution of queries from a provided query file based on
    the index and postings file provided upon initialization. Results are saved into an output file.
    Parsing of queries is handled by converting the boolean expressions into an equivalent python
    expression that is executable.
    """
    eval_index_local = "index"
    eval_globals = {"__builtins__": None}
    replacements = [("AND NOT", "-"), ("AND", "&"), ("OR", "|"), ("NOT", "~"), ("(", " ( "), (")", " ) ")]
    exprs = set(["-", "&", "|", "~", "(", ")"])
    expr_postings_ref = "index[\"%s\"]"

    def __init__(self, index_filename, postings_filename):
        """
        index_filename refers to the dictionary file.
        postings_filename refers to the postings file.
        """
        self.stemmer = PorterStemmer()
        self.index = Index(index_filename, postings_filename)
        self.eval_locals = {self.eval_index_local: self.index}

    def _to_python_expression(self, query):
        """
        Parses a boolean expression by converting the boolean operator keywords into python's bitwise operators,
        and converts the terms into their respective index calls that return SkipList objects.
        The resulting expression is an executable python expression.

        WARNING: NOT SAFE FOR PRODUCTION SYSTEMS. FOR ACADEMIC PURPOSES ONLY.
        """
        query = reduce(lambda q,args: q.replace(*args), self.replacements, query)
        query_list = [x not in self.exprs and self.expr_postings_ref % self.stemmer.stem_word(x.lower()) or x for x in query.split()]
        return " ".join(query_list)

    def _execute_query(self, query):
        """
        Executes the provided query and returns the result

        WARNING: NOT SAFE FOR PRODUCTION SYSTEMS. FOR ACADEMIC PURPOSES ONLY.
        """
        expression = self._to_python_expression(query)
        try:
            result = eval(expression, self.eval_globals, self.eval_locals)
        except SyntaxError as se:
            return "Syntax Error occurred, possible malformed expression during conversion: %s" % expression
        except NameError as ne:
            return "Name Error occured, possible invalid object reference in query: %s" % expression
        else:
            return result

    def process_queries(self, query_filename, output_filename):
        """
        This method takes in a query filename and output filename.
        For every query, it writes the output into a new line.
        """
        try:
            with open(query_filename, 'r') as query_file, open(output_filename, 'w') as output_file:
                for row in query_file:
                    result = self._execute_query(row)
                    output_file.write(str(result) + "\n")
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

    bs = BooleanSearch(args.dict, args.postings)
    bs.process_queries(args.queries, args.output)