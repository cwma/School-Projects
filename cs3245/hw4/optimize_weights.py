#!/usr/bin/env python2.7

"""
Matric: A0112937E
Email:  a0112937@u.nus.edu

This script was used to find optimal weights for the 5 part of speech tag labels.
The weights are used in the cosine similarity calculation between query and
document. As this script was used on an ad hoc basis, arguments pointing towards
the training set are hardcoded. Don't expect it too be too robust.

"""

import search
import subprocess
import sys
import random
import multiprocessing
from collections import Counter
from fractions import Fraction
from Queue import Queue

class SearchWorker(multiprocessing.Process):
    """
    Each worker instance has its own patent search instance
    and all the instances will handle performing the search query
    by consuming the queue containing weights to be used for the query.
    """
    
    def __init__(self, event, queue, results):
        """
        initializes a new SearchWorker instance with its own patent search instance.
        reads the files for correct and incorrect queries to be used later.
        """
        multiprocessing.Process.__init__(self)
        self._event = event
        self._queue = queue
        self._results = results
        self._ps = search.PatentSearch("dictionary.txt", "postings.txt")
        self._queries = [self._ps._parse_query("cs3245-hw4\\q1.xml"), self._ps._parse_query("cs3245-hw4\\q2.xml")]
        self._correct = [set(open("cs3245-hw4\\q1-qrels+ve.txt").read().split()), set(open("cs3245-hw4\\q2-qrels+ve.txt").read().split())]
        self._incorrect = [set(open("cs3245-hw4\\q1-qrels-ve.txt").read().split()), set(open("cs3245-hw4\\q2-qrels-ve.txt").read().split())]
        self.daemon = True

    def _do_search(self, weights):
        """
        Performs the search task. Calls private methods directly instead of relying of public methods
        as we optimize for search without query expansion due to time complexity involved.
        """
        pos = 0
        neg = 0
        weights = {label: weight for label, weight in zip(["VERB", "ADVERB", "NOUN", "ADJECTIVE", "OTHER"], weights)}
        for ((terms, tagmap), correct, incorrect) in zip(self._queries, self._correct, self._incorrect):
            query_tfidfs = self._ps._calculate_query_tfidf(terms)
            doc_tfidfs = self._ps._retrieve_doc_tfidf(terms)
            similarities = self._ps._calculate_similarity(query_tfidfs, doc_tfidfs, tagmap, weights)
            results = self._ps._cull_results(similarities)
            results = set(self._ps._rank_results(results, similarities))
            pos += len(results & correct)
            neg += len(results & incorrect)
        return (pos, neg)

    def run(self):
        """run method"""
        self._ps.index._reopen_postings_file()
        while self._event.is_set():
            index, weights = self._queue.get()
            result = self._do_search(weights)
            self._results.put((index, result))
            self._queue.task_done()

class OptimizeWeights():
    """
    Genetic Algorithm to optimise weights for weighted cosine similarity based
    on part of speech tagging category.
    """

    _NUM_WORKERS = multiprocessing.cpu_count()
    population_size = 10000 # number of agents
    selection = 0.1 # random pool size to select best parents from
    culling = 0.3 # % of population to cull and replace every generation
    mutation_rate = 0.1 # mutation rate
    mutation_delta = 0.2 # % range of mutation adjustment
    num_weights = 5 

    def __init__(self):
        """
        initializes the multiprocessing data structures and spawn workers
        """
        self._event = multiprocessing.Event()
        self._queue = multiprocessing.JoinableQueue()
        self._results = multiprocessing.Queue()
        self._spawn_workers()
        self.population = self._seed_population()

    def _spawn_workers(self):
        """spawns the threaded worker class instances"""
        self._event.set()
        self._workers = [SearchWorker(self._event, self._queue, self._results) for x in xrange(self._NUM_WORKERS)]
        [worker.start() for worker in self._workers]

    def _queue_search(self, population):
        """puts the work into the queue for the worker instances to consume"""
        map(self._queue.put, enumerate(population))

    def _normalize(self, weights):
        """normalize values to 1. if all weights are 0 return 0.5 (for crossover average weighted fitness)"""
        sum_weights = sum(map(abs, weights))
        return map(lambda w: sum_weights > 0 and (float(w) / sum_weights) or 0.5, weights)

    def _generate_weights(self):
        """generates a random vector of length num_weights that sums to 1.0"""
        weights = [random.uniform(-1, 1) for x in xrange(self.num_weights)]
        return self._normalize(weights)

    def _seed_population(self):
        """generates the initial population"""
        return [self._generate_weights() for x in xrange(self.population_size)]

    def _select_parents(self):
        """tournament selection"""
        random_selection = random.sample(xrange(self.population_size), int(self.population_size * 0.1))
        return sorted(random_selection, key=lambda s: (self._scores.get(s)[0], self._scores.get(s)[1]), reverse=True)[:2]

    def _crossover(self, parent1, parent2):
        """average weighted crossover"""
        fitness1, fitness2 = self._normalize([self._scores[parent1][0] - self._scores[parent1][1], self._scores[parent2][0] - self._scores[parent1][1]])
        return self._normalize([(fitness1 * p1) + (fitness2 * p2) for p1, p2 in zip(self.population[parent1], self.population[parent2])])

    def _mutate(self, offspring):
        """mutate randomly selected weight by delta and normalize"""
        weight_idx = random.choice(xrange(len(offspring)))
        mutation_modifier = 1 + random.uniform(-self.mutation_delta, self.mutation_delta)
        offspring[weight_idx] *= mutation_modifier
        return self._normalize(offspring)

    def _create_offspring(self):
        """create an offspring using tournament selection and average weighted crossover"""
        parents = self._select_parents()
        offspring = self._crossover(*parents)
        if (random.uniform(0, 1) < self.mutation_rate):
            self._mutate(offspring)
        return offspring
        
    def _next_generation(self, ranks):
        """cull the weakest population and replace them with new offspring"""
        replace = ranks[:int(self.population_size * self.culling)]
        for idx in replace:
            self.population[idx] = self._create_offspring()

    def _report(self, ranks):
        """prints top 5 weights"""
        top5 = ranks[self.population_size-5:]
        for idx in top5[::-1]:
            print "Pos: %s, Neg: %s, Weights: %s" % (self._scores[idx][0], self._scores[idx][1], self.population[idx])
        print "Population Average Pos: %.1f, Neg: %.1f" % (self._total_pos / float(self.population_size), self._total_neg / float(self.population_size))

    def optimize_weights(self, generations):
        """
        feeds the worker instances weights created every new generation
        and then consumes the results once all the workers have completed.
        """
        for gen in xrange(generations):
            print " Generation: %s" % gen
            self._total_pos = 0
            self._total_neg = 0
            self._queue_search(self.population)
            self._queue.join()
            self._scores = {}
            while not self._results.empty():
                (index, (pos, neg)) = self._results.get()
                self._scores[index] = (pos, neg)
                self._total_pos += pos
                self._total_neg += neg
            ranks = sorted(xrange(self.population_size), key=lambda s: (self._scores.get(s)[0], self._scores.get(s)[1]))
            self._report(ranks)
            self._next_generation(ranks)

if __name__ == '__main__':
    ow = OptimizeWeights()
    ow.optimize_weights(100) 