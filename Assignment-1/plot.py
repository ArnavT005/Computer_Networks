import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import sys
import os

print("")

# decide filename, default is hops.csv
filename = "hops.csv"
if len(sys.argv) >= 2:
    filename = sys.argv[1]
    if len(sys.argv) > 2:
        print("Warning: Too many arguments provided!")

# check existence of file
if not os.path.isfile(filename):
    print("Error: File does not exist!")
    exit()

# open csv
print("Generating Graph from hops.csv")
data_frame = pd.read_csv(filename) 
xData = data_frame["Hop No."]
yData = data_frame["Round Trip Time (in ms)"]
plt.plot(xData, yData, 'o:r', ms=5)
plt.xlabel("Hop Number")
plt.ylabel("Round Trip Time (average, in ms)")
plt.title("Traceroute Packet Data (0 RTT denotes timeout)")
plt.xticks(np.arange(0, len(xData) + 1, step=1))
plt.yticks(np.arange(0, (np.max(yData) // 5 + 2) * 5, step=5))
plt.minorticks_on()
plt.grid(linestyle="--", which="major")
for i in range(0, len(xData)):
    x = xData[i]
    y = yData[i]
    plt.annotate(xy=[x, y], text=str(y) +"ms", ha="center", verticalalignment="bottom")
plt.savefig("graph.jpg")
print("Graph saved in file graph.jpg\n")
print("Program terminated successfully.")

exit()


