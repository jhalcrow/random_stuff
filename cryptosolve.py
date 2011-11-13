from __future__ import division
from string import maketrans, ascii_letters, lowercase
from collections import Counter
from math import log, exp
from operator import add
from random import randint, random
from copy import copy
import re
#from numpy import sum
from collections import defaultdict
import sys

class CryptoSolver(object):
    
    def __init__(self, gram_len=3, alpha=0.1):
        self.gram_counts = Counter()
        self.letter_counts = Counter()
        self.gram_len = gram_len
        self.chars = ascii_letters# + '.'
        #self.chars = lowercase
        self.alpha = alpha

    def make_grams(self, src):
        grams = [src[i:i+self.gram_len] for i in xrange(len(src)-self.gram_len)]
        return grams

    def train(self, src):
        clean = re.sub('[^A-Za-z.]','', src)
        self.gram_counts.update(self.make_grams(clean))
        self.letter_counts.update(clean)

        gram_norm = float(sum(v for g,v in self.gram_counts.items()))
        char_norm = float(sum(v for c,v in self.letter_counts.items()))

        self.smooth = log(self.alpha / gram_norm)

        self.gram_ll = {g:log(v / gram_norm) for g,v in self.gram_counts.items()}
        self.letter_ll = defaultdict(lambda: log(self.alpha / char_norm))
        self.letter_ll.update({c:log(v / char_norm) for c,v in self.letter_counts.items()})


    def likelihood(self, trans, test):
        transtab = maketrans(trans, self.chars)
        test_trans = test.translate(transtab)
        grams = self.make_grams(test.translate(transtab))
        def ll(g):
            if g in self.gram_ll:
                return self.gram_ll[g]
            else:
                return self.smooth
        gramsll = sum(ll(g) for g in grams)
        #letterll = sum(self.letter_ll[c] for c in test_trans)
        return gramsll


    def clean(self, str):
        clean = re.sub('[^A-Za-z.]','', str)
        return clean

    def guess(self, crypt):
        crypt_clean = self.clean(crypt)
        crypt_counts = Counter(crypt_clean)
        crypt_letters = sorted(list(set(crypt_clean)), key=lambda c:-crypt_counts[c])
        letters = sorted(list(self.chars), key=lambda c: -self.letter_ll[c])
        guess = [None for i in xrange(len(self.chars))]
        
        for (cl, l) in zip(crypt_letters, letters):
            i = self.chars.index(l)
            guess[i] = cl

        assigned = set(guess); assigned.discard(None)
        unassigned = list(set(self.chars).difference(assigned))

        for i in xrange(len(guess)):
            if guess[i] is None:
                guess[i] = unassigned[0]
                unassigned = unassigned[1:]
        return ''.join(guess)


    def solve(self, crypt, guess=None, perms=1, iters=100, log_accept=log(0.1)):
        if guess is None:
            cur = self.guess(crypt)
        else:
            cur = copy(guess)

        cur_ll = self.likelihood(cur, crypt)
        C = len(self.chars)

        best_guess = cur
        best_ll = cur_ll
        print 'Initial likelihood: %f' % self.likelihood(cur, crypt)
        for n in xrange(iters):
            guess = list(cur)
            for p in xrange(perms):
                i, j = randint(0, C-1), randint(0, C-1)
                guess[i], guess[j] = guess[j], guess[i]
            guess = ''.join(guess)
            guess_ll = self.likelihood(guess, crypt)
            P = accept_prob(-cur_ll, -guess_ll, n, iters)
            if P > random():
                cur = guess
                cur_ll = guess_ll
            if cur_ll > best_ll:
                print cur_ll
                best_ll = cur_ll
                best_guess = cur
            if n % 1000 == 0:
                print 'Iteration %d: %f' % (n, self.likelihood(cur, crypt))
                print '\tTemperature: %f\tAccept prob: %f' % (temperature(n, iters), P)
                #cur = best_guess
                #cur_ll = best_ll

        print 'Final likelihood: %f' % best_ll
        print 'Translation: %s' %  crypt.translate(maketrans(best_guess, self.chars))
        return best_guess

def exp_temperature(it, it_max):
    return 200 * exp( -3 *  it / it_max)

def lin_temperature(it, it_max):
    return 500 * (1 - it / it_max)

temperature = exp_temperature

def accept_prob(l0, l, it, it_max):
    return exp(-max(0, l - l0) / temperature(it, it_max))

if __name__ == '__main__':
    crypt = '''
      LiYJtYgeYHBzdduYYgzdFtHuYtYHuYuYdYuuNJRFzduYYczDJzFeuNkYO
  jufYJYuHZrjGZNkTNkYJgYgHuYcYgNRJYcFzDHBYgjuYFiHFWzjiHCYFi
  YduYYczDFzcNgFuNGjFYkzeNYgzdduYYgzdFtHuYHJckiHuRYdzuFiYDN
  dWzjtNgiFiHFWzjuYkYNCYgzjukYkzcYzukHJRYFNFNdWzjtHJFNFFiHF
  WzjkHJkiHJRYFiYgzdFtHuYzujgYeNYkYgzdNFNJJYtduYYeuzRuHDgHJ
  cFiHFWzjBJztWzjkHJczFiYgYFiNJRg
    '''
    solver = CryptoSolver()
    solver.train(open(sys.argv[1]).read())
    print 'Translation %s' % solver.solve(crypt, iters=100000)
