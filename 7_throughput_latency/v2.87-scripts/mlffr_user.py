from trex_stl_lib.api import *
import time
import argparse 
import numpy as np 
import os 
import pandas as pd
import sys
from os.path import expanduser

if __name__ == "__main__":
    #start = time.time()
    parser = argparse.ArgumentParser(description='Information about Data')
    parser.add_argument('-d', dest="directory", type=str, help='Directory', required=True)
    parser.add_argument('-v', dest="version", type=str, help='Name of version (e.g o1, o2, s0, s1, s2, s3, s4)', required=True)
    parser.add_argument('-r', dest="run", type=str, help='Number of the run', default="0")
    parser.add_argument('-tx', dest="tx", type=int, help='Port # you want to send packets through', default=0)
    parser.add_argument('-rx', dest="rx", type=int, help='Port # you want to measure recieve packets', default=1)
    parser.add_argument('-t', dest="time", type=int, help='How long(secs) you want to send packets', default=60)
    parser.add_argument('-mS', dest="multStart", type=float, help='Multiplier start rate or the send rate in Mpps', default=1)
    parser.add_argument('-mE', dest="multEnd", type=float, help='Multiplier end rate or the end send rate in Mpps', default=15)
    parser.add_argument('-i', dest="increment", type=float, help='Increment Multiplier by', default=1)
    parser.add_argument('-b', dest="benchmark", type=str, help=f"xdp1 or xdp_fw", required=True)
    args = parser.parse_args()

    # get node0
    f = open("node0.config", "r")
    node0 = f.read()
    node0 = node0.strip('\n')
    f.close()

    c = STLClient(server='127.0.0.1')
    found = True 
    rate = args.multStart
    while found: 
        if (rate  > args.multEnd):
            found = True 
            break
        # load xdp program 
        print("Loading...")
        os.system(f"ssh -p 22 {node0} \"sh -c 'python3 -u /usr/local/trex-configuration/scripts/load_xdp_user.py -b {args.benchmark} -v {args.version.lower()} -m {round(rate)} -r {args.run} -d {args.directory} &'\"")

        try:
            c.connect() # connect to server
            c.reset(ports = 0)
            c.add_profile(filename="stl/udp_for_benchmarks.py", ports=0, kwargs={"packet_len": 64, "stream_count": 1})
            c.start(ports = 0, duration = args.time, mult=f"{rate}mpps")
            time.sleep(0.5)
            pps = 10
            print(f"Start: {rate}")
            while (pps > 1):
                stats = c.get_stats()
                #print(pps)
                time.sleep(0.5)
                pps = c.get_stats()[args.tx]["tx_pps"]
            #c.wait_on_traffic(ports = 0)
            print(f"Completed {rate}")
            print("Unloading...")
            os.system(f"ssh -p 22 {node0} 'python3 -u /usr/local/trex-configuration/scripts/unload_xdp.py; exit'")
        except STLError as e:
            print(e)

        finally:
            c.disconnect()
        rate +=args.increment
        
        time.sleep(5)

    # end = time.time()
    # print(f"Total Time: {end-start}")
    print("DONE")