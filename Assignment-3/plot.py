import matplotlib.pyplot as plt
import pandas as pd
import sys

file = sys.argv[1]
df = pd.read_csv(file, header=None)
data = df.to_numpy()
m, n = data.shape
time = data[:, 0]
oldCwnd = data[:, 1]
newCwnd = data[:, 2]
plt.plot(time, newCwnd, label="Congestion Window size")
plt.xlabel("Time (in seconds)")
plt.ylabel("Congestion Window size (in bytes)")
plt.legend()
plt.savefig(file + ".png")