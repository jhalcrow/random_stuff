from itertools import cycle, izip
import bisect

import numpy as np
import scipy
from scipy import stats
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def generate_mondrian_1D(budget, interval = (0,1)):
    """
    Randomly makes a draw from a 1D Mondrian process.
    From Roy and Teh "The Mondrian Process"
    budget corresponds to lambda in that paper
    """
    cost = stats.expon.rvs(size=1, scale = 1./ budget)[0]
    if cost > budget:
        return [interval]
    else:
        new_budget = budget - cost
        cut = np.random.random() * (interval[1] - interval[0]) + interval[0]
        return [generate_mondrian_1D(new_budget, (interval[0], cut))] + \
               [generate_mondrian_1D(new_budget, (cut, interval[1]))]

def generate_mondrian(budget, domain = [(0,1), (0,1)]):
    """
    Randomly makes a draw from a Mondrian process of arbitrary dimension.
    From Roy and Teh "The Mondrian Process"
    budget corresponds to lambda in that paper
    """
    cost = stats.expon.rvs(size=1, scale = 1./ budget)[0]
    if cost > budget:
        return [domain]
    else:
        new_budget = budget - cost
        len_cumsum = [0,] + list(np.cumsum([i[1] - i[0] for i in domain]))
        cut = np.random.random() * len_cumsum[-1]
        d = bisect.bisect(len_cumsum, cut) - 1# The cut axis
        split_size = cut - len_cumsum[d] # Where the cut falls in that axis
        piece1 = domain[0:d] + [(domain[d][0], domain[d][0] + split_size)] + domain[d+1:]
        piece2 = domain[0:d] + [(domain[d][0] + split_size, domain[d][1])] + domain[d+1:]
        return [generate_mondrian(new_budget, piece1)] + [generate_mondrian(new_budget, piece2)]
    
def draw_mondrian_1D(intervals, ax, colorindex=0):
    colors = ['red', 'blue', 'yellow']
    for iv in intervals:
        if type(iv[0]) is tuple:
            rect = mpatches.Rectangle((iv[0][0],0), iv[0][1], 1, facecolor=colors[np.random.randint(len(colors))], edgecolor='black')
            ax.add_patch(rect)
        else:
            draw_mondrian_1D(iv, ax)
        
def draw_mondrian_2D(intervals, ax, colors=cycle(['red', 'blue', 'yellow', 'white', 'brown'])):
        
    for (iv,color) in izip(intervals, colors):
        if type(iv[0]) is tuple:
            ll = (iv[0][0], iv[1][0])
            width = iv[0][1] - iv[0][0]
            height = iv[1][1] - iv[1][0]
            print 'Drawing rectangle at (%f,%f), width=%f, height=%f' % (ll[0], ll[1], width, height)
            print 'color is %s' % color
            rect = mpatches.Rectangle(ll, width, height, facecolor=color, edgecolor='black')
            ax.add_patch(rect)
        else:
            draw_mondrian_2D(iv, ax, colors)
