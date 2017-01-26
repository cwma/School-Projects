#!/usr/bin/env python2.7

"""
Matric: A0112937E
Email:  a0112937@u.nus.edu

This script contains parsing methods used by both index.py and search.py
Methods are used to handle tokenizing and processing of text, parsing
of xml files and expansion of document terms.

"""
import nltk
import cPickle
from string import ascii_lowercase
from xml.etree import ElementTree
from functools import partial
from nltk import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.stem.porter import PorterStemmer

# stop words and general terms we filter out as they're not useful
stemmer = PorterStemmer()
stop_words = set(stopwords.words('english'))
stop_words |= set(["(", ")", ",", ".", "|", "'", ";", '"', "e.g", "i.e"])
stop_words |= set(ascii_lowercase)
general_terms = set(map(stemmer.stem_word, ["describe", "devices", "means", "using", "relevant", "documents", "technology", "effect"
                                        "including", "equipment", "form", "apparatus", "general", "contain", "characterised",
                                        "method", "system", "product", "process", "special", "provide", "involve", "arrangement"]))
#lemmatizer = WordNetLemmatizer()

# maps all part of speech tag into 4 categories
pos_simplify = {}
map(lambda postag: pos_simplify.__setitem__(postag, "VERB"), ["VB", "VBZ", "VBD", "VBG", "VBN", "VBP"])
map(lambda postag: pos_simplify.__setitem__(postag, "ADVERB"), ["RB", "RBR", "RBS"])
map(lambda postag: pos_simplify.__setitem__(postag, "NOUN"), ["NN", "NNP", "NNPS", "NNS"])
map(lambda postag: pos_simplify.__setitem__(postag, "ADJECTIVE"), ["JJ", "JJR", "JJS"])

def remove_numerals(term, result):
    """
    remove all numerals from a list of strings
    """
    try:
        int(term)
    except ValueError:
        result.append(term)

def tokenize_text(text):
    """
    tokenizes a text and removes stop words and numerals.
    """
    text = text.encode('utf-8')
    text = word_tokenize(text.lower())
    text = filter(lambda term: term not in stop_words, text)
    tokenized_text = []
    map(partial(remove_numerals, result=tokenized_text), text)
    return tokenized_text

def process_text(tokenized_text, postag=False):
    """
    processes a list of tokenized terms into stemmed form and 
    remove unwanted terms. If postag is True return the map of 
    term to part of speech tag.
    """
    tagmap = {}
    try:
        if postag:
            tagmap = get_pos_tags(tokenized_text)
    except LookupError:
        print "WARNING: POS TAGGER NOT INSTALLED"
        print "OPERATING AT REDUCED PERFORMANCE"
    try:
        #tokenized_text = map(lemmatizer.lemmatize, tokenized_text)
        tokenized_text = map(stemmer.stem_word, tokenized_text)
        tokenized_text = filter(lambda term: term not in general_terms, tokenized_text)
        return (tokenized_text, tagmap)
    except Exception, e:
        return ([], {})

def parse_corpus_xml(file_path):
    """
    parses the corpus xml file into its tokenized text,
    processed terms and a list of ipc scheme labels.
    """
    file_tree = ElementTree.parse(file_path)
    file_root = file_tree.getroot()
    text = ""
    ipc = []
    for child in file_root:
        if child.attrib['name'] == "Title":
            text += child.text + " "
        if child.attrib['name'] == "Abstract":
            text += child.text.split('|')[0] + " "
        if child.attrib['name'] == "All IPC":
            ipc = child.text.strip().split('|')
    tokenized_text = tokenize_text(text)
    terms, tagmap = process_text(tokenized_text)
    ipc_list = [parse_corpus_ipc(x) for x in ipc]
    return (tokenized_text, terms, ipc_list)

def parse_corpus_ipc(ipc_string):
    """
    handles parsing of the ipc scheme labels.
    """
    ipc_string = ipc_string.strip().lower()
    ipc_class = ipc_string[:3]
    ipc_subclass = ipc_string[:4]
    break_pos = ipc_string.find('/')
    ipc_group_a = ""
    ipc_group_b = ""
    if ipc_string[-1] != '/':
        ipc_group_a = ipc_string[4:break_pos]
        ipc_group_b = ipc_string[break_pos+1:]
    return (ipc_class, ipc_subclass, ipc_group_a, ipc_group_b)

def expand_terms(ipc, terms, ipc_list):
    """
    performs document expansion.
    Documents are expanded by adding terms retrieved from its associated
    IPC Scheme label description.
    """
    labels = []
    for (ipc_class, ipc_subclass, ipc_group_a, ipc_group_b) in ipc_list:
            labels.append(ipc_class)
            labels.append(ipc_subclass)
            ipc_group_b = len(ipc_group_b) == 0 and "0" + ipc_group_b or ipc_group_b
            labels.append(ipc_subclass + "0"*(4-len(ipc_group_a)) + ipc_group_a + "0" * 6) # category level label
            labels.append(ipc_subclass + "0"*(4-len(ipc_group_a)) + ipc_group_a + ipc_group_b + "0"*(6-len(ipc_group_b))) # full label
    for label in labels:
        try:
            terms.extend(ipc[label])
        except KeyError:
            pass
    return terms

def get_pos_tags(tokenized_text):
    """
    retrieves the simplified part of speech tags of terms
    and returns a map of it.
    """
    tagmap = {}
    tags = set(nltk.pos_tag(tokenized_text))
    for term, tag in tags:
        try:
            tag = pos_simplify[tag]
        except KeyError:
            tag = "OTHER"
        tagmap[stemmer.stem_word(term)] = tag
    return tagmap