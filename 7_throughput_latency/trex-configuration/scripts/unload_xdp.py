import os
from os.path import expanduser
import argparse 

home = expanduser("~")
home = "/usr/local"
# read interfaces
f = open(f"{home}/trex-configuration/scripts/device.config", "r")
device = f.read()
device = device.strip('\n')
f.close()
i = open(f"{home}/trex-configuration/scripts/{device}.config", "r")
interfaces = i.read().split("\n")
for i in interfaces:
    os.system(f"sudo pkill -f \"{i}\"")
    os.system(f"sudo ip link set dev {i} xdp off")
os.chdir(f"{home}/throughput-experiments")
os.system(f"sudo rm -f *.o")
