#include <WinSock2.h>
#include <WS2tcpip.h>
#include <iphlpapi.h>
#include <IcmpAPI.h>
#include <cstdlib>
#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <set>

bool isInteger(std::string const&);
bool stringCompare(std::string const&, std::string const&);

int main(int argc, char** argv) {
    // process command line arguments
    if(argc < 2) {
        std::cout << "Error: Host name not specified!" << std::endl;
        return 1;
    }
    int maxHops = 30, timeout = 4000, numPackets = 5;
    bool graph = true;
    bool war = false;
    if(argc > 2) {
        // process flags
        for(int i = 2; i < argc;) {
            if(i + 1 == argc) {
                if(stringCompare(argv[i], "-ng")) {
                    graph = false;
                }
                else {
                    war = true;                        
                }
                break;
            }
            if(stringCompare(argv[i], "-h")) {
                if(isInteger(argv[i + 1])) {
                    maxHops = std::stoi(argv[i + 1]);
                    if(maxHops == 0) {
                        war = true;
                        break;
                    }
                    i += 2;
                }
                else {
                    war = true;
                    break;
                }
            }
            else if(stringCompare(argv[i], "-w")) {
                if(isInteger(argv[i + 1])) {
                    timeout = std::stoi(argv[i + 1]);
                    if(timeout == 0) {
                        war = true;
                        break;
                    }
                    i += 2;
                }
                else {
                    war = true;
                    break;
                }
            }
            else if(stringCompare(argv[i], "-n")) {
                if(isInteger(argv[i + 1])) {
                    numPackets = std::stoi(argv[i + 1]);
                    if(numPackets == 0) {
                        war = true;
                        break;
                    }
                    i += 2;
                }
                else {
                    war = true;
                    break;
                }
            }
            else if(stringCompare(argv[i], "-ng")){
                graph = false;
                i ++;
            }
            else {
                war = true;
                break;
            }
        }
        if(war) {
            std::cout << "Warning: Input format is incorrect! Some parameters may be missing/unwanted/incorrect.\n";
            std::cout << "Default parameters will be used." << std::endl;
            maxHops = 30;
            timeout = 4000;
            numPackets = 5;
            graph = true;
        }
    }
    // initialize winsock api
    WSADATA wsaData;
    if(WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        std::cout << "Error: Winsock could not initialize!" << std::endl;
        return 1;
    }
    // get host ip from name
    ADDRINFOA socketInfo {0, AF_INET, SOCK_STREAM, 0, 0, nullptr, nullptr, nullptr}, *result;
    if(getaddrinfo(argv[1], nullptr, &socketInfo, &result) != 0) {
        std::cout << "Error: Unable to resolve host!\n";
        std::cout << "Troubleshooting tips:\n";
        std::cout << "  1) Ensure that the host name is valid before trying again.\n";
        std::cout << "  2) Try doing a successful \"nslookup <host_name>\" before running tracert again." << std::endl;
        WSACleanup();
        return 1;
    }
    IN_ADDR destinationAddress = ((sockaddr_in*) (result->ai_addr))->sin_addr;
    std::string ipAddrString = inet_ntoa(destinationAddress);
    IPAddr ipAddrStruct = inet_addr(ipAddrString.c_str());
    freeaddrinfo(result);

    // tracing route to destinationAddress
    std::cout << "\nTracing route to " << argv[1] << " [" << ipAddrString << "]\n";
    std::cout << "over a maximum of " + std::to_string(maxHops) + " hops\n" << std::endl;

    // open handle
    HANDLE icmpHandle = IcmpCreateFile();
    if(icmpHandle == INVALID_HANDLE_VALUE) {
        std::cout << "Error: Unable to send ICMP packets!" << std::endl;
        WSACleanup();
        return 1;
    }

    // create packets and buffer
    char packet[32] = "Ping message!";
    unsigned long responseSize = 40 + sizeof(ICMP_ECHO_REPLY), status;
    void *responseBuffer = malloc(responseSize);
    if(responseBuffer == nullptr) {
        std::cout << "Error: Unable to allocate memory resources!" << std::endl;
        WSACleanup();
        return 1;
    }
    
    // set options
    IP_OPTION_INFORMATION options {1, 0, IP_FLAG_DF, 0, nullptr};
    IN_ADDR router;
    bool flag = false;
    int ARTT, count;
    std::vector<int> RTT(numPackets);
    std::vector<std::string> IP(numPackets);
    std::set<std::string> ipAddr;

    // create csv file
    std::ofstream fout("hops.csv");
    if(!fout) {
        std::cout << "Error: Unable to open hops.csv file" << std::endl;
        WSACleanup();
        free(responseBuffer);
        return 1;
    }
    fout << "Hop No.,Round Trip Time (in ms)\n";

    // max maxHops hops
    while(options.Ttl <= maxHops && !flag) {
        ARTT = 0;
        count = 0;
        ipAddr.clear();
        int temp = -1;
        std::cout << "  " << (int) options.Ttl << "\t";
        // send numPackets packets
        for(int i = 0; i < numPackets; i ++) {
            IP[i] = "***.***.***.***";
            IcmpSendEcho(icmpHandle, ipAddrStruct, (void*) packet, 32, &options, responseBuffer, responseSize, timeout);
            status = ((ICMP_ECHO_REPLY*) responseBuffer)->Status;
            if(status == 0 || status == 11013) {
                if(status == 0) {
                    flag = true;
                }
                RTT[i] = ((ICMP_ECHO_REPLY*) responseBuffer)->RoundTripTime;
                ARTT += RTT[i];
                count ++;
                if(RTT[i] == 0) {
                    std::cout << "<1 ms\t";
                }
                else {
                    std::cout << RTT[i] << " ms\t";
                }
                router.S_un.S_addr = ((ICMP_ECHO_REPLY*) responseBuffer)->Address;
                IP[i] = inet_ntoa(router);
                if(ipAddr.find(IP[i]) == ipAddr.end()) {
                    ipAddr.insert(IP[i]);
                }
                if(temp == -1) {
                    temp = i;
                }
            }
            else {
                std::cout << "*\t";
            }
        }
        if(count == 0) {
            std::cout << "Request timed out. " << std::endl;
            fout << std::to_string((int) options.Ttl) << ",0\n";
        }
        else {
            if(ARTT >= count) {
                std::cout << "(Average RTT: " << ARTT / count << " ms)\t";
                fout << std::to_string((int) options.Ttl) << "," << std::to_string(ARTT / count) << "\n";
            }
            else {
                std::cout << "(Average RTT: <1 ms)\t";
                fout << std::to_string((int) options.Ttl) << "," << std::to_string((float) ARTT / count) << "\n";
            }
            if(ipAddr.size() < 2) {
                std::cout << IP[temp] << std::endl;
            }
            else {
                for(int i = 0; i < numPackets; i ++) {
                    std::cout << IP[i] << "\t";
                }
                std::cout << std::endl;
            }
        }
        options.Ttl ++;
    }
    // cleanup
    std::cout << "\nTrace complete." << std::endl;
    fout.close();
    WSACleanup();
    free(responseBuffer);

    // create graph, if required
    if(graph) {
        system("python plot.py");
    }
    
    return 0;
}

bool isInteger(std::string const& arg) {
    int n = arg.size();
    for(int i = 0; i < n; i ++) {
        if(arg[i] >= '0' && arg[i] <= '9') {
            continue;
        }
        else {
            return false;
        }
    }
    return true;
}

bool stringCompare(std::string const& str1, std::string const& str2) {
    int n1 = str1.size(), n2 = str2.size();
    if(n1 != n2) {
        return false;
    }
    for(int i = 0; i < n1; i ++) {
        if(str1[i] != str2[i]) {
            return false;
        }
    }
    return true;
}