import os
import time 
import sys
import argparse 
from os.path import expanduser

default_ranges = {
    "xdp2": (8.5, 10.5, 0.1),
    "xdp_fw": (1,15,1),
    "xdp_router_ipv4": (1,2.4, 0.1),
    "xdp_fwd": (4.4, 5.4, 0.1)
}
benchmarks = ["xdp2", "xdp_fw", "xdp_router_ipv4", "xdp_fwd"]
parser = argparse.ArgumentParser()
parser.add_argument('-b', dest="benchmark", type=str, help=f"Benchmark {str(benchmarks)}", required=True)
parser.add_argument('-d', dest="directory", type=str, help='Directory', required=True)
parser.add_argument('-v', dest="version", type=str, help='Name of version (e.g o1, o2, k0, k1, k2, k3, k4)', required=False)
parser.add_argument('-n', dest="number", type=int, help='Number of times each version should run', default=5)
parser.add_argument('-c', dest="cores", type=int, help='Number of cores', default=14)
parser.add_argument('-mS', dest="start", type=int, help='Start Mpps')
parser.add_argument('-mE', dest="end", type=int, help='End Mpps')
parser.add_argument('-i', dest="increment", type=int, help='Increment Mpps')
args = parser.parse_args()
home = expanduser("~")

versionList = []
if (args.version):
    versionList.append(args.version)
else:
    versionList = ["o1", "o2", "k0", "k1", "k2", "k3", "k4"]
if (not args.benchmark in benchmarks):
    print(f"Invalid benchmark name. {str(benchmarks)}")

if not args.start:
    start = default_ranges[args.benchmark][0]
else:
    start = args.start
if not args.end:
    end = default_ranges[args.benchmark][1]
else:
    end = args.end
if not args.increment:
    increment = default_ranges[args.benchmark][2]
else:
    increment = args.increment

if not os.path.exists(f"{home}/{args.directory}"):
    os.mkdir(f"{home}/{args.directory}")

# Read node0 configuration
f = open("node0.config", "r")
node0 = f.read()
node0 = node0.strip('\n')
f.close()
# Fix: a T-Rex instance left running from an interrupted previous attempt
# holds the ZMQ port and makes every subsequent launch fail with
# "ERROR encountered while configuring TRex system". Always clear it first.
os.system("sudo pkill t-rex; sleep 2")
print(f"Starting T-rex")
os.system(f"nohup sudo ./t-rex-64 -i -c {args.cores} > $HOME/log.txt &")
time.sleep(60)
with open(f'{home}/log.txt') as f:
    if 'ERROR encountered while configuring TRex system' in f.read():
        print("Error while starting Trex")
        exit(0)
for x in range (args.number):
    print(f"Iteration {x}")
    for v in versionList:
        print(f"Running {v}")
        print(f"Loading xdp...")
        os.system(f"ssh -p 22 {node0} \"sh -c 'python3 -u /usr/local/trex-configuration/scripts/load_xdp.py -b {args.benchmark} -v {v} 1>log.txt 2>err.txt &'\"")
        time.sleep(60)
        print("MLFFR...")
        os.system(f"python3 -u mlffr.py -d {args.directory} -v {v} -r {x} -mS {start} -mE {end} -i {increment} -rx 0")
        print("Unloading xdp")
        os.system(f"ssh -p 22 {node0} 'python3 /usr/local/trex-configuration/scripts/unload_xdp.py; exit'")
        time.sleep(60)

print("Stopping T-rex and all its children")
os.system("sudo pkill t-rex")
time.sleep(200)

print("Completed Full Script")