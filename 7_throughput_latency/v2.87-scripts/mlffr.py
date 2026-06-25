from trex_stl_lib.api import *
import time
import argparse 
import numpy as np 
import os 
import pandas as pd
import sys
from os.path import expanduser
home = expanduser("~")

def write_averages(name, data, args, label):
     # Write Averages to file
    myfile = f"{home}/{args.directory}/MLFFR_{args.version}_{label}.txt"
    df = pd.DataFrame(data)
    df = df.rename(columns={name: f"{args.run}"})
    if (os.path.exists(myfile)):
        df1 = pd.read_csv(myfile)
        df1[f"{args.run}"] = df[f"{args.run}"]
        df = df1
    print(df)
    df.to_csv(myfile,index=False)

if __name__ == "__main__":
    sys.path.append(f"{os.getcwd()}/automation/trex_control_plane/interactive")
    start = time.time()
    parser = argparse.ArgumentParser(description='Information about Data')
    parser.add_argument('-d', dest="directory", type=str, help='Directory', required=True)
    parser.add_argument('-v', dest="version", type=str, help='Name of version (e.g o1, o2, s0, s1, s2, s3, s4)', required=True)
    parser.add_argument('-r', dest="run", type=str, help='Number of the run', default="0")
    parser.add_argument('-tx', dest="tx", type=int, help='Port # you want to send packets through', default=0)
    parser.add_argument('-rx', dest="rx", type=int, help='Port # you want to measure recieve packets', default=1)
    parser.add_argument('-t', dest="time", type=int, help='How long(secs) you want to send packets', default=100)
    parser.add_argument('-mS', dest="multStart", type=float, help='Multiplier start rate or the send rate in Mpps', default=1)
    parser.add_argument('-mE', dest="multEnd", type=float, help='Multiplier end rate or the end send rate in Mpps', default=2)
    parser.add_argument('-i', dest="increment", type=float, help='Increment Multiplier by', default=0.1)
    args = parser.parse_args()

    c = STLClient(server='127.0.0.1')
    found = True 
    rate = args.multStart
    idealRate = 100
    diff = []
    maxL = []
    minL = []
    avgL = []
    fullData = pd.DataFrame()
    while found: 
        if (rate  > args.multEnd):
            found = True 
            break
        try:
            c.connect() # connect to server
            c.reset(ports = 0)
            c.add_profile(filename="stl/udp_for_benchmarks.py", ports=0, kwargs={"packet_len": 64, "stream_count": 1})
            c.start(ports = 0, duration = args.time, mult=f"{rate}mpps")
            time.sleep(0.5)
            rx_pps = []
            tx_pps = []
            min_l = []
            avg_l = []
            max_l = []
            pps = 10
            print(f"Start: {rate}")
            #print(f"Rate Difference: {rate - idealRate}")
            while (pps > 1):
                stats = c.get_stats()
                if stats[args.tx]["tx_pps"] >= (rate-0.01) * pow(10,6):
                    rx_pps.append(stats[args.rx]["rx_pps"])
                    tx_pps.append(stats[args.tx]["tx_pps"])
                    latency_stats = stats["latency"][2]["latency"]
                    min_l.append(latency_stats["total_min"])
                    max_l.append(latency_stats["total_max"])
                    avg_l.append(latency_stats["average"])
                time.sleep(0.5)
                pps = c.get_stats()[args.tx]["tx_pps"]
                #print(pps)
            temp = pd.DataFrame()
            temp[f"{rate}_tx"] = tx_pps
            temp[f"{rate}_rx"] = rx_pps
            temp[f"{rate}_min"] = min_l
            temp[f"{rate}_max"] = max_l
            temp[f"{rate}_avg"] = avg_l
            fullData = pd.concat([fullData, temp], axis=1)
            # print(temp)
            # print(fullData)
            diffArr = np.abs(np.subtract(rx_pps, tx_pps))
            diff_mean = np.mean(diffArr)
            print(f"rx = {np.mean(rx_pps)}")
            print(f"tx = {np.mean(tx_pps)}")
            print(f"diff = {diff_mean}")
            print(f"maxL = {np.mean(max_l)}")
            print(f"minL = {np.mean(min_l)}")
            print(f"avgL = {np.mean(avg_l)}")
            if (diff_mean > 10000 and idealRate == 100):
                if (len(diff) > 0):
                    idealRate = diff[-1]["Rate"]
            diff.append({"Rate": rate, "Diff": diff_mean})
            maxL.append({"Rate": rate, "Max": np.mean(max_l)})
            minL.append({"Rate": rate, "Min": np.mean(min_l)})
            avgL.append({"Rate": rate, "Avg": np.mean(avg_l)})
            #c.wait_on_traffic(ports = 0)
        except STLError as e:
            print(e)

        finally:
            c.disconnect()
        rate +=args.increment
        
        time.sleep(10)

    # Write Full Data to file 
    fullData.to_csv(f"{home}/{args.directory}/MLFFR_{args.version}_{args.run}_full.txt",index=False)

    # Write Averages to file
    write_averages("Diff", diff, args, "t")
    write_averages("Max", maxL, args, "maxL")
    write_averages("Min", minL, args, "minL")
    write_averages("Avg", avgL, args, "avgL")
    end = time.time()
    print(f"Ideal rate: {idealRate}")
    print(f"Total Time: {end-start}")
    print("DONE")