import os
from os.path import expanduser
import sys
import argparse 

interfaces = ["ens3f1"]
programs = {
    "xdp1": ("xdp1_kern", "completed-programs/kernel_samples_xdp1_kern_xdp1_runtime_debug"),
    "xdp_map_access": ("xdp_map_access_kern", "completed-programs/simple_fw_xdp_map_access_runtime_debug"),
}
parser = argparse.ArgumentParser(description='Information about Data')
parser.add_argument('-b', dest="benchmark", type=str, help=f"Benchmark {str(programs.keys())}", required=True)
parser.add_argument('-v', dest="version", type=str, help='Name of version (e.g O1, O2, K0, K1, K2, K3, K4)', required=True)
parser.add_argument('-m', dest="rate", type=str, help='MLFFR Rate', required=True)
parser.add_argument('-r', dest="run", type=str, help='Run Number', required=True)
parser.add_argument('-d', dest="directory", type=str, help='Directory', required=True)
args = parser.parse_args()

HOME = expanduser("~")
home = "/usr/local"
# read interfaces
f = open(f"{home}/trex-configuration/scripts/device.config", "r")
device = f.read()
device = device.strip('\n')
f.close()
i = open(f"{home}/trex-configuration/scripts/{device}.config", "r")
interfaces = i.read().split("\n")

os.chdir(f"{home}/throughput-experiments")
for x in interfaces:
    os.system(f"sudo ip link set dev {x} xdp off")

number = list(args.version)[1]
if "k" in args.version.lower():
    os.system(f"sudo cp {programs[args.benchmark][1]}/top-progs/{programs[args.benchmark][0]}{number}.o {programs[args.benchmark][0]}.o")
else:
    os.system(f"sudo cp {args.version.upper()}/{programs[args.benchmark][0]}.o .")

# create directory
if not os.path.isdir(f"{HOME}/{args.directory}"):
    os.mkdir(f"{HOME}/{args.directory}")

# load program
if args.benchmark == "xdp1":
    os.system(f"sh -c 'sudo ./xdp1 -N {interfaces[0]}' 1>{HOME}/{args.directory}/{args.version}_{args.run}_{args.rate}.txt 2>{HOME}/err.txt &")
elif args.benchmark == "xdp_map_access":
    os.system(f"sh -c 'sudo ./xdp_map_access -N {interfaces[0]}' 1>{HOME}/{args.directory}/{args.version}_{args.run}_{args.rate}.txt 2>{HOME}/err.txt &")