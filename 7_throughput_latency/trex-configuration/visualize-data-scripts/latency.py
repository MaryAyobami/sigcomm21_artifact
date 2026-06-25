import pandas as pd 
import matplotlib.pyplot as plt
import os 
import numpy as np 
import argparse 
from enum import Enum   
import numpy 

def summarize(args):
    file = pd.read_csv(f'{args.directory}/MLFFR_{args.version}_{args.gtype}L.txt', index_col=0)
    file.index = file.index.to_series().apply(lambda x: np.round(x, 2))
    arr = np.array(file.loc[:, "0"])
    #print(arr)
    diff = numpy.diff(arr)
    #print(diff)
    for x in range(len(diff)):
        if diff[x] > 20:
            break
    indexes = [file.index[x-2], file.index[x-1], file.index[x], file.index[x+1], file.index[x+2]]
    print("MLFFR: ")
    print(file.loc[indexes, :])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Information about Data')
    parser.add_argument('-d', dest="directory", type=str, help='Directory', required=True)
    parser.add_argument('-type', dest="gtype", type=str, help='max, min or avg', required=True)
    parser.add_argument('-v', dest="version", type=str, help='(e.g. o1, o2 etc.)', required=True)
    parser.add_argument('-b', dest="benchmark", type=str, help='Name of Benchmark', required=True)
    parser.add_argument('-show', action='store_true')
    args = parser.parse_args()
    if not args.gtype in ["max", "min", "avg"]:
        print("Wrong type")
        exit(0)
    file = pd.read_csv(f'{args.directory}/MLFFR_{args.version}_{args.gtype}L.txt', index_col=0)
    file.index = file.index.to_series().apply(lambda x: np.round(x, 2))
    fig = plt.figure()
    plt.plot(file, marker="o")                 
    plt.title(f'Measuring {args.benchmark} {args.version} {args.gtype.upper()} Latency')
    plt.xlabel('TX rate (Mpps)',)
    plt.ylabel('Latency')
    labels = []
    for x in range(len(file.columns)):
        labels.append(f"{args.version} Run " + file.columns[x])
    plt.legend(labels)
    if (args.show):
        plt.show()
    
    fig.savefig(f'{args.directory}/{args.version}_{args.gtype}L.png', bbox_inches='tight')
    summarize(args)