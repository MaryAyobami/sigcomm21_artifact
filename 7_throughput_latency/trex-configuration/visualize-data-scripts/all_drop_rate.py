import pandas as pd 
import matplotlib.pyplot as plt
import os 

import argparse 

def dropRate(directory, benchmark, run):
    df = pd.DataFrame()
    file = pd.read_csv(f'{directory}/MLFFR_o1_t.txt', index_col=0)
    df["index"] = list(file.index)
    df.set_index("index", inplace=True)
    versions = ["o1", "o2", "k0", "k1", "k2", "k3", "k4"]
    if benchmark == "xdp2" or benchmark == "xdp_router_ipv4":
        versions.remove("k2")
    for i in versions:
        file = pd.read_csv(f'{directory}/MLFFR_{i}_t.txt', index_col=0)
        df[i] = file[run]
    #print(df)
    fig = plt.figure()
    plt.plot(df, marker="o")                      
    plt.title(f'Measuring {benchmark} Drop Rate')
    plt.xlabel('TX rate (Mpps)',)
    plt.ylabel('Average Drop Rate in pps')
    plt.legend(df.columns)
    savePath = f'{directory}/drop/'
    if not os.path.exists(savePath):
        os.makedirs(savePath)
    fig.savefig(f'{savePath}/{run}.png', bbox_inches='tight')
    #plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Information about Data')
    parser.add_argument('-d', dest="directory", type=str, help='Directory', required=True)
    parser.add_argument('-r', dest="run", type=str, help='Run Number', required=True)
    parser.add_argument('-b', dest="benchmark", type=str, help='Benchmark', required=True)
    args = parser.parse_args()
    dropRate(args.directory, args.benchmark, args.run)
