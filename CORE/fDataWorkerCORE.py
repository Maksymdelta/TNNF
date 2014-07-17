# ---------------------------------------------------------------------# IMPORTS


import numpy as np
from numpy import *
from numpy import dot, sqrt, diag
from numpy.linalg import eigh
import theano
import theano.tensor as T
import csv as csv
import cPickle
import time
from scipy.cluster.vq import *
import matplotlib.pylab as plt
from PIL import Image, ImageOps, ImageFilter


# ---------------------------------------------------------------------# ROLLOUT


def rollOut(l):
    numClasses = 4
    n = l.shape[0]
    l = l.reshape((1, -1))
    l = np.tile(l, (numClasses, 1))
    g = np.array(range(1, numClasses + 1)).reshape((-1, 1))
    g = np.tile(g, (1, n))
    res = l == g * 1.0
    return res


# ---------------------------------------------------------------------# DATA GENERATOR


def noisedSinGen(number=10000, phase=0):
    # Number of points
    time = np.linspace(-np.pi * 10, np.pi * 10, number)
    # y=(    sin(x - pi /2) + cos(x * 2 * pi)         ) / 10 + 0.5
    # series = (np.sin((time+phase)-np.pi/2) + np.cos((time+phase)*2.0*np.pi))/10.0+0.5
    series = np.sin(time + phase) / 2 + 0.5
    noise = np.random.uniform(0.0, 0.01, number)
    data = series + noise  # Input data
    # fig = plt.figure(figsize=(200, 9))
    #ax = fig.add_subplot(1, 1, 1)
    #ax.scatter(time, data, s=5, alpha=0.5, color="blue")
    return (time, data)


# ---------------------------------------------------------------------# DATA MANIPULATION


class multiData(BatchMixin):  # Glues data in one block
    def __init__(self, *objs):
        xtuple = ()
        ytuple = ()
        for obj in objs:
            xtuple += (obj.X,)
            ytuple += (obj.Y,)
        self.X = np.concatenate(xtuple, axis=1)
        self.Y = np.concatenate(ytuple, axis=1)
        self.number = self.X.shape[1]
        self.input = self.X.shape[0]


# ---------------------------------------------------------------------#


class BatchMixin(object):
    REPORT = "OK"

    def miniBatch(self, number):  # Method for minibatch return
        minIndex = np.random.randint(0, self.number, number)
        self.miniX = self.X[:, minIndex]
        return self.miniX, minIndex


# ---------------------------------------------------------------------#

class csvDataLoader(BatchMixin):  # Data loader from csv file
    def __init__(self, folder, startColumn=1, skip=1):
        data = np.loadtxt(open(folder, "rb"), delimiter=",", skiprows=skip)
        data = data.astype('float')
        if len(data.shape) == 1:  # Fixed (1000,) bug
            data = np.reshape(data, (data.shape[0], 1))
        self.X = data[:, startColumn:].T
        self.Y = data[:, 0:startColumn].T
        self.number = len(data)
        self.input = len(self.X)


# ---------------------------------------------------------------------#


class DataMutate(object):
    @staticmethod
    def deNormalizer(ia, afterzero=20):  # Mapped 0-255 to 0-1 and round to 5 digit after zero
        ia = np.array(ia)
        ia = np.around(ia / 255.0, decimals=afterzero)
        return ia

    @staticmethod
    def Normalizer(ia):  # Mapped to 0-255
        min = np.min(ia)
        max = np.max(ia)
        koeff = 255 / (max - min)
        ia = (ia - min) * koeff
        return ia

    @staticmethod
    def PCAW(X, epsilon=0.01):  # PCA Whitening. One picture for now
        M = X.mean(axis=0)
        X = X - M
        C = dot(X, X.T)  # / size(x, 1) for not only one picture
        U, S, V = linalg.svd(C)
        # Original formula: xZCAwhite = U * diag(1.0 / sqrt(diag(S) + epsilon)) * U' * x;
        # http://ufldl.stanford.edu/wiki/index.php/Implementing_PCA/Whitening
        ex1 = diag(1.0 / sqrt(S + epsilon))
        ex2 = dot(U, ex1)
        ex3 = dot(ex2, U.T)
        xPCAWhite = dot(ex3, X)
        # Second way
        # V, D = eigh(C)
        # ex1 = diag(1.0 / sqrt(V + epsilon))
        # ex2 = dot(D, ex1)
        # ex3 = dot(ex2, D.T)
        # xPCAWhite = dot(ex3, X)
        return xPCAWhite


# ---------------------------------------------------------------------#