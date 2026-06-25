import pandas as pd 
import matplotlib.pyplot as plt
import os 
import argparse 

def rx(directory, benchmark, run, version):
    df = pd.DataFrame()
    file = pd.read_csv(f'{directory}/MLFFR_o1_t.txt', index_col=0)
    df["index"] = list(file.index)
    df.set_index("index", inplace=True)
    versions = ["k0", "k1", "k2", "k3", "k4", "o1", "o2"]
    if version != "":
        versions = [version]
    if len(versions) > 1 and benchmark == "xdp2" or benchmark == "xdp_router_ipv4":
        versions.remove("k2")
    for i in versions:
        file = pd.read_csv(f'{directory}/MLFFR_{i}_{run}_full.txt', index_col=0)
        arr = []
        for x in file.columns:
            if "rx" in x:
                arr.append(file[x].mean()/pow(10,6))
        df[i] = arr

    #print(df)
    fig = plt.figure()
    plt.plot(df, marker="o")                      
    plt.title(f'{benchmark} Throughput')
    plt.xlabel('TX rate (Mpps)',)
    plt.ylabel('RX rate (Mpps)')
    plt.legend(df.columns)
    savePath = f'{directory}/rx/'
    if not os.path.exists(savePath):
        os.makedirs(savePath)
    fig.savefig(f'{savePath}/{run}.png', bbox_inches='tight')
    return df

def rx_avg(directory, benchmark, runs):
    df = pd.DataFrame()
    for x in range(runs):
        new_df = rx(directory, benchmark, str(x), "")
        df = df.merge(new_df, how="outer", on=None, left_index=True, right_index=True)
    
    versions = ["k0", "k1", "k2", "k3", "k4", "o1", "o2"]
    if benchmark == "xdp2" or benchmark == "xdp_router_ipv4":
        versions.remove("k2")
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
    df.to_csv(f"{directory}/rx-data.csv")
    #print(means)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Information about Data')
    parser.add_argument('-d', dest="directory", type=str, help='Directory', required=True)
    parser.add_argument('-r', dest="run", type=str, help='Run Number', required=True)
    parser.add_argument('-b', dest="benchmark", type=str, help='Benchmark', required=True)
    parser.add_argument('-v', dest="version", type=str, help='(e.g. o1, o2 etc.)', default="")
    args = parser.parse_args()
    #rx_avg(args.directory, args.benchmark)
    rx(args.directory, args.benchmark, args.run, args.version)
