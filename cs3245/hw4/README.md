This is the README file for A0112937E's submission a0112937@u.nus.edu

== General Notes about this assignment ==

First a general overview of my submission.

My Patent Search system implements a vector space model of lnc.ltc from hw#3, with a number of additional features. Document expansion using descriptions from IPC scheme titles. Query expansion using terms taken from the top returned results from an initial search. A stop list with additional words determined manually based due to non-usefulness. Augmenting similarity scores by determining what IPC label a query belongs to by seeing which IPC labels are most prominent amount top results. And finally, a crazy idea i had where the cosine similarity result for each term is weighted based on its part of speech tag, with weights optimized by a genetic algorithm trained on the provided training set. 

In addition, indexing employs multiprocessing to fully utilize all a CPU's available logical processors to index the corpus files. The genetic algorithm in optimize weights also does the same. This follows a simple producer/consumer pattern typical of multithreaded/process applications.

For both queries and the corpus, the title and descriptions are concatenated and processed into a bag of words and are treated as such. The terms are processed to remove all stop words and some general terms such that they ideally describe the patent itself without additional frills.

Indexing.

Indexing follows similarly to hw#3 with the dictionary and postings file. In addition, I store the following information:
- docid: list of ipc labels
- docid: list of raw term ids (terms not stemmed)
- raw_term_id: raw term (terms not stemmed)
 
This additional information is used for the weighted cosine based on part of speech tagging hence the need for pre-stemmed terms, and the ipc labels are used for determining which label a query most likely belongs to so that relevant documents have a higher similarity. Indexing also employs what I call document expansion, where additional terms are sourced from the descriptions the IPC titles that each document has. The IPC titles are sourced from http://www.wipo.int/classifications/ipc/en/ITsupport/Version20160101/, and are saved in a preprocessed pickled dictionary file for convenience.

Search.

In addition to the lnc.ltc scheme, we have:
- Weighted cosine similarity based on part of speech tagging
- - For every query term, based on its part of speech label, the resulting cosine similarity will be weighted by predetermined optimized weights. The weights were optimized using a genetic algorithm trained on the provided test set. Surprisingly this works well to rank the results better. Even if we do not have a top k cutoff, this is still useful for query expansion and using results to determine query ipc label as we want the top results to be as accurate as possible.

- Query Expansion
- - First perform a regular lnc.ltc search, and retrieve the results. For initial results select only the top results and use them as candidates for query expansion. Count all the terms in the candidates, and use the top most prevalent terms to expand the query. The search is then repeated with the new query terms. With the new results, use the top results to find what ipc labels are most prevalent and consider those most correct to the query. Modify similarity scores based on documents retrieved with the same label and rerank to get final results. This last component is only useful if we use a top k selection to cull results below a certain threshold that we believe are not correct.

Optimizing weights using a genetic algorithm

This is really just a fancy way of brute forcing the weights that seem to give the best results given the limited test set. I am surprised that it actually has some small benefit to the final results. My rationale for this idea is that different types of words are more useful than others, and thought that i could apply part of speech tagging and a genetic algorithm to determine what type of words are more useful than others. Perhaps another means of doing this would be to have in addition to tf.idf, and inverse part of speech document frequency, where we get pos tags for the entire corpus and determine which type of words are less common and thus more useful in describing uniqueness rather than generalized terms.

== Files included with this submission ==
index.py 
python script that performs indexing of patent corpus

search.py
python script that performs the patent search

parsers.py
Text processing utility methods used by both index.py and search.py

optimize_weights.py
genetic algorithm for optimizing weights for cosine similarity based on part of speech tagging

README.txt
this file itself!

dictionary.txt
serialized python dictionary data structure 

postings.txt
contains the postings and tfidf values of terms in documents

IPC.txt
a serialized python dictionary containing ipc labels from
http://www.wipo.int/ipc/itos4ipc/ITSupport_and_download_area/20160101/IPC_scheme_title_list/EN_ipc_title_list_20160101.zip

== Statement of individual work ==

Please initial one of the following statements.

[x] I, A0112937E, certify that I have followed the CS 3245 Information
Retrieval class guidelines for homework assignments.  In particular, I
expressly vow that I have followed the Facebook rule in discussing
with others in doing the assignment and did not take notes (digital or
printed) from the discussions.  

[ ] I, A0112937E did not follow the class rules regarding homework
assignment, because of the following reason:

Not Applicable

I suggest that I should be graded as follows:

Every line of code was written by myself and I should be graded as such.

== References ==

https://docs.python.org/2/
general standard library use reference

https://github.com/2016-cs3243-group-1/AlphaTetris/blob/master/AlphaTetris.py
Genetic algorithm was based off of code i wrote for another module which i adapted to use here. 