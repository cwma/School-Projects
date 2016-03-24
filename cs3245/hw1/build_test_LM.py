#!/usr/bin/env python2.7

"""
Matric: A0112937E
Email:  a0112937@u.nus.edu

This script contains 2 classes.
The LanguageModel class contains the full scope of the solution as required by the homework #1 assignment.
The LanguageModelNB subclass implements nltk's Naive Bayesian Classifier that I wrote for my own interest.

The solution includes optional arguments to enable the usage of padding, case folding, and variable ngrams
Usage is as follows:

$python build_test_LM.py -b input-file-for-building-LM -t input-file-for-testing-LM -o output-file

The following are optional flags:

[-p] enables padding
[-c] enables case folding
[-n ngram_size] the size of ngrams to be used where 0 < n < 5
[-nb] uses the naive bayes classifier instead of ngrams

"""
import sys
import argparse
import operator
from collections import Counter, defaultdict
from fractions import Fraction
from nltk.util import ngrams
from nltk.classify.naivebayes import NaiveBayesClassifier

NGRAM_SIZE = 4
PAD_TOKEN = "#"
SMOOTHING = 1

class LanguageModel(object):
    """
    LanguageModel is an instance class that takes in a training file name which it will read to 
    build its internal language model based on ngrams that can be used to classify an input text string.
    the classify method can be called to test an input string, or the test_LM method can be called with 
    an input file name and an output file name to process a large number of strings in a batch.

    """

    def __init__(self, train_filename, use_padding=False, fold_cases=False):
        """
        train_filename is a required argument and reference the filename to be used to train the language model
        use_padding is an optional argument that pads the start and end of every sentence in the training data.
        default value is set to False.
        fold_cases is an optional argument that normalizes the training data to all lower case.
        default value is set to False.
        """
        self.use_padding = use_padding
        self.fold_cases = fold_cases
        self.ngram_index = defaultdict(lambda: defaultdict(lambda: SMOOTHING))
        self.ngram_count = Counter()
        self._build_LM(train_filename)

    def _get_ngram_tokens(self, line):
        """this private method is used to take in a line of text and convert it into a list of ngrams"""
        # tokens = ngrams(line.rstrip(), NGRAM_SIZE, pad_left=self.use_padding, pad_right=self.use_padding, pad_symbol=PAD_TOKEN)
        # return ["".join(token) for token in tokens]
        line = line.rstrip()
        if self.fold_cases:
            line = line.lower()
        if self.use_padding:
            line = "%s%s%s" % (PAD_TOKEN * (NGRAM_SIZE - 1), line, PAD_TOKEN * (NGRAM_SIZE - 1))
        return [line[x: x + NGRAM_SIZE] for x in range(len(line) - (NGRAM_SIZE - 1))]

    def _add_to_index(self, language, ngram_tokens):
        """this private method simply adds the input ngrams based on its language to the appropriate dictionary entries"""
        for token in ngram_tokens:
            self.ngram_index[token][language] += 1
            self.ngram_count[language] += 1

    def _build_LM(self, train_filename):
        """
        this private method opens the train file, and calls the respective private methods to
        tokenize each line into ngrams and to add them into the dictionaries.
        It will then adjust the total count of ngrams based on the smoothing value
        """
        ngrams = defaultdict(lambda: [])
        try:
            with open(train_filename, 'r') as train_file:
                for row in train_file:
                    row = row.split(" ")
                    language, line = (row[0], " ".join(row[1:]))
                    ngram_tokens = self._get_ngram_tokens(line)
                    self._add_to_index(language, ngram_tokens)
                    ngrams[language].append(ngram_tokens)
        except IOError as error:
            print "Error encounted when attempting to open and read the train file: %s" % train_filename
            sys.exit(error.args[1])
        else:
            for language in self.ngram_count:
                self.ngram_count[language] += len(self.ngram_index) * SMOOTHING

    def _known_threshold_met(self, ngram_tokens, known_tokens):
        """
        this private method checks if the number of known versus unknown tokens exceeds a certain predefined
        limit for the input to be considered as part of the known classification labels instead of other
        """
        total, known, unknown = (len(ngram_tokens), len(known_tokens), len(ngram_tokens) - len(known_tokens))
        if Fraction(known, total) > 0.25:
            return True
        return False

    def classify(self, ngram_tokens):
        """
        This method takes in the ngrams to be tested and calculates the probability of it
        being a language in the LanguageModel. If it does not meet the classification threshold it 
        is labled as "other"
        """
        results = []
        known_tokens = [token for token in ngram_tokens if token in self.ngram_index] # no wild cards
        for language, count in self.ngram_count.items():
            # if known_tokens is not empty, convert ngram counts of each language into its fractional value and reduce to find its probability
            # otherwise return 0
            probability = known_tokens and reduce(operator.mul, map(lambda token: Fraction(self.ngram_index[token][language], count), known_tokens)) or 0
            results.append({'language': language, 'probability': probability})
        results = sorted(results, key=operator.itemgetter('probability'), reverse=True)
        if self._known_threshold_met(ngram_tokens, known_tokens):
            return results[0]['language']
        return 'other'

    def test_LM(self, test_filename, output_filename):
        """
        This method takes in a test file name and an output filename
        and attempts to classify each line in the test file and outputs
        the results into the output file.
        """
        try:
            with open(test_filename, 'r') as test_file, open(output_filename, 'w') as output_file:
                for row in test_file:
                    ngram_tokens = self._get_ngram_tokens(row)
                    label = self.classify(ngram_tokens)
                    output = "%s %s" % (label, row)
                    output_file.write(output)
        except IOError as error:
            print "Error encounted when attempting to test the language model"
            sys.exit(error.args[1])

class LanguageModelNB(LanguageModel):
    """
    LanguageModelNB is a subclass of LanguageModel that uses nltk's
    Naive Bayes Classifier as a means for language classification instead of ngrams.
    """

    def __init__(self, train_filename, use_padding=False, fold_cases=False):
        self.use_padding = use_padding
        self.fold_cases = fold_cases
        self._build_LM(train_filename)

    def _get_ngram_tokens(self, line):
        if self.fold_cases:
            line = line.lower()
        tokens = ngrams(line.rstrip(), NGRAM_SIZE, pad_left=self.use_padding, pad_right=self.use_padding, pad_symbol=PAD_TOKEN)
        return {"".join(token) : True for token in tokens}

    def _build_LM(self, train_filename):
        """
        this private method opens the train file, and calls the respective private methods to
        tokenize each line into ngrams and uses it to train the Naive Bayes Classifier.
        """
        training_data = []
        try:
            with open(train_filename, 'r') as train_file:
                for row in train_file:
                    row = row.split(" ")
                    language, line = (row[0], " ".join(row[1:]))
                    ngram_tokens = self._get_ngram_tokens(line)
                    training_data.append((ngram_tokens, language))
            self.classifier = NaiveBayesClassifier.train(training_data)
        except IOError as error:
            print "Error encounted when attempting to open and read the train file: %s" % train_filename
            sys.exit(error.args[1])

    def classify(self, ngram_tokens):
        """
        This method takes in the ngrams to be tested and calls the Naive Bayes Classifier
        to classify them. For results that have a probability of less than 0.5 they are
        given an "others" label.
        """
        probabilities = self.classifier.prob_classify(ngram_tokens)
        results = sorted([{"language": label, "probability": probabilities.prob(label)} for label in probabilities.samples()], 
                            key=operator.itemgetter('probability'), reverse=True)
        if results[0]['probability'] > 0.5:
            return results[0]["language"]
        return 'other'

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    # mandatory arguments
    parser.add_argument("-b", required=True, help="input file for training the language model", metavar="train_file", dest="train_file")
    parser.add_argument("-t", required=True, help="input file for testing the language model", metavar="test_file", dest="test_file")
    parser.add_argument("-o", required=True, help="output file containing test results", metavar="output_file", dest="output_file")

    # optional arguments
    parser.add_argument("-n", type=int, help="choose number of ngrams", choices=range(1,5), metavar="ngrams", dest="ngrams")
    parser.add_argument('-p', action='store_true', help="flag for using padding in ngrams", dest="p")
    parser.add_argument('-c', action='store_true', help="flag for folding cases in ngrams", dest="c")
    parser.add_argument('-nb', action='store_true', help="flag for using NaiveBayes Classifier", dest="nb")

    args = parser.parse_args()
    if args.ngrams:
        NGRAM_SIZE = int(args.ngrams)
    if args.nb:
        LM = LanguageModelNB(args.train_file, args.p, args.c)
    else:
        LM = LanguageModel(args.train_file, args.p, args.c)
    LM.test_LM(args.test_file, args.output_file)