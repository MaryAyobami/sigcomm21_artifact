import pandas as pd 
import matplotlib.pyplot as plt
import os 
import argparse 
import numpy as np 

def parse_file(name, benchmark):
    # Using readlines()
    file1 = open(name, 'r')
    Lines = file1.readlines()
    
    data = []
    # Strips the newline character
    for line in Lines:
        contain = "proto 17:"
        if benchmark == "xdp_map_access":
            contain = "proto 23:"
        if contain in line:
            newLine = line.replace(contain,'')
            newLine = newLine.strip('\n')
            newLine = newLine.strip()
            newLine = newLine.replace('pkt/s','')
            data.append(int(newLine))
    return data[10:20]

def get_mlffr(directory, run, benchmark, version):
    df = pd.DataFrame()
    if (benchmark == "xdp1"):
        rates = np.arange(10,30,1)
    elif (benchmark == "xdp_map_access"):
        rates = np.arange(12,23,1)
    df["index"] = list(rates)
    df.set_index("index", inplace=True)
    if version:
        versions = [version]
    else:
        versions = ["k0", "k1", "k2", "k3", "k4", "o1", "o2"]
    for v in versions:
        arr = []
        for x in rates:
            data = parse_file(f'{directory}/{v}_{run}_{x}.txt', benchmark)
            arr.append(sum(data) / len(data) / 10 ** 6)
        df[v] = arr
    fig = plt.figure()
    plt.plot(df, marker="o")  
    plt.title(f'{benchmark} run {run} Throughput')
    plt.xlabel('TX rate (Mpps)',)
    plt.ylabel('RX rate (Mpps)')
    plt.legend(df.columns)
    savePath = f'{directory}/rx/'
    if not os.path.exists(savePath):
        os.makedirs(savePath)
    fig.savefig(f'{savePath}/{run}.png', bbox_inches='tight')
    return df
    #plt.show()

def mlffr_averages(directory, benchmark, run, version):
    df = pd.DataFrame()
    for x in range (0, run):
        new_df = get_mlffr(directory, x, benchmark, None)
        df = df.merge(new_df, how="outer", on=None, left_index=True, right_index=True, suffixes=('_1', '_2'))
    if run <= 1:
        return
    versions = ["k0", "k1", "k2", "k3", "k4", "o1", "o2"]
    if (version):
        versions = [version]
    for v in versions:
        temp = df.loc[:, df.columns.str.contains(v)]
        temp['mean'] = temp.mean(axis=1)
        #print(file)
        df[f"{v} mean"] = temp['mean']
    means = df.loc[:, df.columns.str.contains("mean")]
    fig = plt.figure()
    plt.plot(means, marker="o")                      
    plt.title(f'{benchmark} AVG Throughput')
    plt.xlabel('TX rate (Mpps)',)
    plt.ylabel('RX rate (Mpps)')
    plt.legend(means.columns)
    savePath = f'{directory}/rx/'
    if not os.path.exists(savePath):
        os.makedirs(savePath)
    fig.savefig(f'{savePath}/avg.png', bbox_inches='tight')
    df.to_csv(f"{directory}/full_parsed_data.csv", index=True)
    df.loc[:, df.columns.str.contains("mean")].to_csv(f"{directory}/avg_parsed_data.csv", index=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Information about Data')
    parser.add_argument('-d', dest="directory", type=str, help='Directory', required=True)
    parser.add_argument('-r', dest="runs", type=int, help='# of runs for each version', default=3)
    parser.add_argument('-b', dest="benchmark", type=str, help='Name of Benchmark', required=True)
    parser.add_argument('-v', dest="version", type=str, help='Version', default="o1")
    parser.add_argument('-average', action='store_true')
    args = parser.parse_args()
    if (args.average):
        mlffr_averages(args.directory, args.benchmark, args.runs, None)
    else: 
        get_mlffr(args.directory, args.runs, args.benchmark, args.version)

