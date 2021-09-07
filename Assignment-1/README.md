# Assignment-1  
---
---
## Directory Information
- **assets** folder consists of screenshots/text-data of command-line/Wireshark experimentation
- **tracert.cpp** and **plot.py** are traceroute implementation and plotting script respectively
- **Report.pdf** is the assignment report (containing all three parts)

## Compilation Instructions  
- Open terminal  
- Type in the command line ```g++ tracert.cpp -o tracert -lws2_32 -liphlpapi```  
> Note: The program uses Windows Socket API for sending/receiving packets, hence, it may not compile successfully on other OS  
> Note: Plotting script uses Pandas, Numpy and Matplotlib libraries. Hence, ensure that these modules are installed before using plot.py  

## Execution Instructions  
- Open terminal  
- Compile tracert.cpp file  
- Execute the program by typing ```./tracert.exe hostname [-h] [-w] [-n] [-ng]```  
### Parameter details:  
- *hostname* is the public domain name to which the route needs to be traced
- **-h**: Specify maximum number of hops (positive integer)
- **-w**: Specify the waiting time in milliseconds (positive integer)
- **-n**: Specify the number of ICMP packets to be sent per hop (positive integer)
- **-ng**: Use this flag if plotting script should not be called at the end of program
> Note: [] denotes optional flags  
> Note: Flags can be used in any order, however, the second argument should always be the hostname 
---
---
