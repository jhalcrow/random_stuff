#!/usr/bin/env python

# 7 August 2010
# My attempt to produce random words, because I can't think
# of a screen name that isn't already taken.

import os
import numpy as np
from collections import defaultdict
import itertools as it
import re
import bisect



class CountingTrie(object):
	'''
	A Trie that counts the number of times it has seen something
	'''
	EOW = None
	
	def __init__(self):
		self.counts = defaultdict(int)
		self.children = defaultdict(CountingTrie)
		
	def add_chain(self, sequence):
		if len(sequence) > 0:
			(next,rest) = (sequence[0], sequence[1:])
			self.counts[next] += 1
			child = self.children[next]
			child.add_chain(rest)
		else:
			self.counts[self.EOW] += 1
			
def ngrams(word, N):
	for w in range(len(word) - N + 1):
		yield word[w:w+N]			

def sample_multinomial(weighted_outcomes):
	outcomes = weighted_outcomes.keys()
	pdf = [weighted_outcomes[o] for o in outcomes]
	cdf = np.cumsum(pdf)
	r = np.random.random()*cdf[-1]
	
	sample_idx = bisect.bisect(cdf, r)
	return outcomes[sample_idx]
					
class PositionalNGramMarkov(object):
	'''
	Attempt #1
	Markov chain sampler for ngrams, each state in the 
	chain corresponds to a position and an ngram.  
	Every word produced by this must have been observed
	already.
	'''
	
	def __init__(self, N):
		self.N = N
		self.trie = CountingTrie()
	
	def count_transitions(self, text):
		tnorm = text.lower()
		tclean = re.sub(r'[^a-z ]','',tnorm)
		tokens = tclean.split()
		for tok in tokens:
			self.trie.add_chain([n for n in ngrams(tok,self.N)])
	
	def sampler(self):
		sample = 0
		trie = self.trie
		while sample is not None:
			sample = sample_multinomial(trie.counts)
			trie = trie.children[sample]
			yield sample
			
	def sample(self):
		ngrams = [s for s in self.sampler() if s is not None]
		if len(ngrams) == 0:
			return ''

		return ''.join([ng[0] for ng in ngrams[:-1]]) + ngrams[-1]
					
	
class NGramMarkov(object):
	'''
	Attempt #2
	This time the states are simply ngrams with no regard
	to position in the word.  Output is much better!
	'''
	EOW = None
	
	def __init__(self, N):
		self.N = N
		self.transitions = defaultdict(lambda: defaultdict(int))
		
	def count_transitions(self, text):
		tnorm = text.lower()
		tclean = re.sub(r'[^a-z ]','',tnorm)
		tokens = tclean.split()
		for tok in tokens:
			last = None
			for ngram in ngrams(tok, self.N):
				if last is not None:
					ltrans = self.transitions[last]
					ltrans[ngram] += 1
				last = ngram
			self.transitions[last][self.EOW] += 1
		
	def sampler(self):
		states = self.transitions.keys()
		state = states[np.random.randint(len(states))]
		while state is not None:
			yield state
			trans = self.transitions[state]
			if len(trans) == 0:
				state = None
			else:
				state = sample_multinomial(trans)
			
				
	def sample(self):
		ngrams = [s for s in self.sampler() if s is not None]
		if len(ngrams) == 0:
			return ''

		return ''.join([ng[0] for ng in ngrams[:-1]]) + ngrams[-1]
					

# Produce 20 random words
if __name__ == '__main__':
	ngm = NGramMarkov(3)
	sysdicts = os.listdir('/usr/share/dict/')
	sysdicts_txt = ' '.join(' '.join(w.strip() 
		for w in open('/usr/share/dict/' + d)) for d in sysdicts)
		
	ngm.count_transitions(sysdicts_txt)
	
	for i in range(20):
		print ngm.sample()
		

	
				
