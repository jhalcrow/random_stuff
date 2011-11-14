from __future__ import division
from string import maketrans, ascii_letters
from collections import Counter
from math import log, exp
from difflib import get_close_matches
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


    def solve(self, crypt, words, guess=None, perms=1, iters=100, log_accept=log(0.1)):
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
                best_ll = cur_ll
                best_guess = cur

            if n % 1000 == 0:
                print 'Iteration %d: %f' % (n, self.likelihood(cur, crypt))
                print '\tTemperature: %f\tAccept prob: %f' % (exp_temperature(n, iters), P)
                #cur = best_guess
                #cur_ll = best_ll

        print 'Final likelihood: %f' % best_ll
        translation = crypt.translate(maketrans(best_guess, self.chars))
        print 'Char only guess: \n' + translation
        spacing = space_annealing(translation, words, 5000)

        print 'Best guess: %s' % ' '.join(space_text(translation, spacing))
        print spacing
        return best_guess

def space_text(letters, spacing):
    return [letters[i:j] for (i, j) in zip([0] + spacing, spacing + [len(letters)])]

def exp_temperature(it, it_max):
    return 200 * exp( -3 *  it / it_max)

def lin_temperature(it, it_max):
    return 500 * (1 - it / it_max)

def spacing_init(raw, words):
    lens = sorted(words.keys(), key=lambda k: -k)
    blocks = []
    for l in lens:
        matches = [w for w in words[l] if raw.find(w) >= 0]
        for m in matches:
            start = raw.find(m)
            end = start + l
            for b0, b1, w in blocks:
                if not (start >= b0 and start < b1) and not (end > b0 and end <= b1):
                    blocks += [(start, end, w)]
                

def space_annealing(raw, words, iters, temp=exp_temperature):
    cur_spacing = [i for i in xrange(len(raw)) if i % 5 == 0]
    cur_spacing_energy = space_energy(raw, cur_spacing, words)
    best_spacing_energy = cur_spacing_energy
    best_spacing = cur_spacing
    for n in xrange(iters):
        if n % 500 == 0:
            print 'Iteration: %d\tSpacing Energy:%f' % (n, cur_spacing_energy)
        guess_spacing = space_guess(cur_spacing, len(raw))
        guess_energy = space_energy(raw, guess_spacing, words)
        if accept_prob(cur_spacing_energy*10, guess_energy*10, n, iters, temp) > random():
            cur_spacing = guess_spacing
            cur_spacing_energy = guess_energy

        if cur_spacing_energy < best_spacing_energy:
            best_spacing = cur_spacing
            best_spacing_energy = cur_spacing_energy

    print ' '.join(space_text(raw, best_spacing))
    return best_spacing



def space_guess(cur, max_space):
    '''
    Randomly either delete, add, or move a space
    '''
    r = random()
    guess = copy(cur)
    if len(cur) > 0 and r < 1/3 or len(cur) == max_space - 1: # Delete case
        i = randint(0, len(cur) - 1)
        guess.pop(i)
    elif len(cur) > 0 and r > 2/3:
        i = randint(0, len(cur) - 1)
        if random() < 0.5:
            guess[i] += 1
        else:
            guess[i] -= 1

    else:
        while True:
            new = randint(1, max_space)
            if new not in guess:
                break
        guess += [new,]
        guess.sort()

    guess = sorted(list(set(guess)))
    return guess
    
def space_energy(trans, spacing, words):
    e = 0 
    for word in space_text(trans, spacing):
        e += 0.1 * (len(word) - 4)**2
        if not words.has_key(len(word)):
            e += len(word) ** 2
            continue
        matches = get_close_matches(word, words[len(word)])
        if len(matches) == 0:
            e += len(word)
        else:
            e += min(map(lambda w: hamm_dist(word, w), matches))
    return e


def hamm_dist(a, b):
    '''
    Hamming distance between two strings, the number of letters that don't match
    '''
    if len(a) != len(b):
        return max(len(a), len(b))

    d = 0
    for la, lb in zip(a, b):
        if la != lb:
            d += 1

    return d


def accept_prob(l0, l, it, it_max, temperature=exp_temperature):
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
    crypt = re.sub('[^A-Za-z]','', crypt)
    #words = list(set(w.strip().lower() for w in open('/usr/share/dict/words')))
    words = set()
    len_count = Counter()
    for l in open('alice.txt'):
        line = [w.strip() for w in re.sub('[^a-z ]', ' ', l.lower()).split()]
        len_count.update(map(len, line))
        words.update(line)

    words_by_len = {l:[w for w in words if len(w) == l] for l in xrange(3, 10)}
    solver = CryptoSolver()
    solver.train(open(sys.argv[1]).read())
    print 'Translation %s' % solver.solve(crypt, words_by_len, iters=100000)
