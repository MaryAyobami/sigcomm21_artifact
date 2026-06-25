import pandas as pd 
import matplotlib.pyplot as plt
import os 
#import seaborn as sns
import argparse 

def latency_graphs(directory, benchmark, run, gtype):
    if not gtype in ["max", "min", "avg"]:
        print("Wrong type")
        exit(0)
    df = pd.DataFrame()
    file = pd.read_csv(f'{directory}/MLFFR_o1_{gtype}L.txt', index_col=0)
    df["index"] = list(file.index)
    df.set_index("index", inplace=True)
    versions = ["k0", "k1", "k2", "k3", "k4", "o1", "o2"]
    if benchmark == "xdp2" or benchmark == "xdp_router_ipv4":
        versions.remove("k2")
    for i in versions:
        file = pd.read_csv(f'{directory}/MLFFR_{i}_{gtype}L.txt', index_col=0)
        df[i] = file[run]

    #print(df)
    fig = plt.figure()
    ax = plt.axes()
    plt.plot(df, marker="o")                      
    plt.title(f'{benchmark} {gtype} Latency')
    plt.xlabel('TX rate (Mpps)',)
    plt.ylabel('Latency (µs)')
    plt.legend(df.columns)
    savePath = f'{directory}/{gtype}L/'
    if not os.path.exists(savePath):
        os.makedirs(savePath)
    fig.savefig(f'{savePath}/{run}.png', bbox_inches='tight')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Information about Data')
    parser.add_argument('-d', dest="directory", type=str, help='Directory', required=True)
    parser.add_argument('-type', dest="gtype", type=str, help='max, min or avg', required=True)
    parser.add_argument('-r', dest="run", type=str, help='Run Number', required=True)
    parser.add_argument('-b', dest="benchmark", type=str, help='Benchmark', required=True)
    args = parser.parse_args()
    latency_graphs(args.directory, args.benchmark, args.run, args.gtype)
