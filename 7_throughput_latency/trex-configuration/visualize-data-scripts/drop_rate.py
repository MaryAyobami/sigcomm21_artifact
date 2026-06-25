import pandas as pd 
import matplotlib.pyplot as plt
import os 

import argparse 

parser = argparse.ArgumentParser(description='Information about Data')
parser.add_argument('-d', dest="directory", type=str, help='Directory', required=True)
parser.add_argument('-b', dest="benchmark", type=str, help='Benchmark', required=True)
args = parser.parse_args()

file = pd.read_csv(f'{args.directory}/MLFFR_o1_t.txt', index_col=0)
print(file)

plt.plot(file, marker="o")                      
plt.title(f'Measuring {args.benchmark} Throughput')
plt.xlabel('TX rate (Mpps)',)
plt.ylabel('Average Drop Rate in pps')
plt.legend(["Run 1", "Run 2", "Run 3"])
plt.show()