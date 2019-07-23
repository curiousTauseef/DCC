"""Example for doing all steps in code only (other examples require calling different files separately)"""
import torch.nn as nn
import time

from dcc.config import cfg, get_data_dir
from easydict import EasyDict as edict
from dcc.edgeConstruction import compressed_data
import matplotlib.pyplot as plt
from dcc import data_params as dp
from dcc import make_data
from dcc import pretraining
from dcc import extract_feature
from dcc import copyGraph
from dcc import DCC

import IPython


class IdentityNet(nn.Module):
    """Substitute for the autoencoder for visualization and debugging just the clustering part"""

    def __init__(self):
        super(IdentityNet, self).__init__()

    def forward(self, x):
        # internal encoding is x and output is also just x
        return x, x


def run_easy_example(N):
    datadir = get_data_dir(dp.easy.name)
    # first create the data
    X, labels = make_data.make_easy_visual_data(datadir, N)

    # visualize data
    # we know there are 3 classes
    for c in range(3):
        x = X[labels == c, :]
        plt.scatter(x[:, 0], x[:, 1], label=str(c))
    plt.legend()
    plt.show()

    # then construct mkNN graph
    k = 50
    compressed_data(dp.easy.name, N, k, preprocess='none', algo='knn', isPCA=None, format='mat')
    # creates pretrained.mat

    # then pretrain to get features
    args = edict()
    args.db = dp.easy.name
    args.niter = 500
    args.step = 300
    args.lr = 0.001

    # if we need to resume for faster debugging/results
    args.resume = False
    args.level = None

    args.batchsize = 300
    args.ngpu = 1
    args.deviceID = 0
    args.tensorboard = True
    args.h5 = False
    args.id = N
    args.dim = 2
    args.manualSeed = cfg.RNG_SEED
    args.clean_log = True

    # if we comment out the next pretraining step and the identity network, use the latest checkpoint
    index = len(dp.easy.dim) - 1
    net = None
    # if we comment out the next pretraining step we use the identity network
    net = IdentityNet()
    index, net = pretraining.main(args)

    # extract pretrained features
    args.feat = 'pretrained'
    args.torchmodel = 'checkpoint_{}.pth.tar'.format(index)
    extract_feature.main(args, net=net)

    # merge the features and mkNN graph
    args.g = 'pretrained.mat'
    args.out = 'pretrained'
    args.feat = 'pretrained.pkl'
    copyGraph.main(args)

    # actually do DCC
    args.batchsize = cfg.PAIRS_PER_BATCH
    args.nepoch = 500
    args.M = 20
    args.lr = 0.001
    out = DCC.main(args, net=net)


if __name__ == "__main__":
    Ns = [1e2, 1e3, 1e4, 1e5]
    Ns = [int(N) for N in Ns]
    times = []

    for N in Ns:
        start = time.perf_counter()
        run_easy_example(N)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

        for i in range(len(times)):
            print("{} {}".format(Ns[i], times[i]))

    plt.figure()
    plt.plot(Ns, times)
    plt.xlabel("N")
    plt.ylabel("DCC elapsed time (s)")
    plt.show()

    IPython.embed()
