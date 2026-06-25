import os 
import argparse 
from all_drop_rate import *
from all_latency import *
from all_latency_avg import *
from all_drop_rate_avg import *
from rx_plot import *
parser = argparse.ArgumentParser(description='Information about Data')
parser.add_argument('-d', dest="directory", type=str, help='Directory', required=True)
parser.add_argument('-b', dest="benchmark", type=str, help='Benchmark', required=True)
parser.add_argument('-r', dest="runs", type=int, help='Total Number of Runs (greater than 1)', required=True)
args = parser.parse_args()

# generate drop rate graphs
for x in range(args.runs):
    dropRate(args.directory, args.benchmark, str(x))
if (args.runs > 1):
    avg_drop(args.directory, args.benchmark)

# generate latency graphs
for t in ["max", "min", "avg"]:
    for x in range(3):
        latency_graphs(args.directory, args.benchmark, str(x), t)
    if (args.runs > 1):
        avg_latency(args.directory, args.benchmark, t)

# generate rx graphs
if (args.runs > 1):
    rx_avg(args.directory, args.benchmark, args.runs)
else: 
    rx(args.directory, args.benchmark, 0)
