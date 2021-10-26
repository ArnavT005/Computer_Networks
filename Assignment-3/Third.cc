# include <fstream>
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"

using namespace ns3;

// MyApp class from sixth.cc
class MyApp : public Application {
	public:
  		MyApp();
  		virtual ~MyApp();
	    static TypeId GetTypeId(void);
  		void Setup(Ptr<Socket> socket, Address address, uint32_t packetSize, DataRate dataRate);
  		uint32_t m_packetsSent;
	private:
  		virtual void StartApplication(void);
	  	virtual void StopApplication(void);
  		void ScheduleTx (void);
  		void SendPacket (void);
  		Ptr<Socket> m_socket;
  		Address m_peer;
  		uint32_t m_packetSize;
  		DataRate m_dataRate;
  		EventId m_sendEvent;
  		bool m_running;	
};

MyApp::MyApp() {
	m_socket = 0;
    m_packetSize = 0;
    m_dataRate = 0;
    m_running = false;
    m_packetsSent = 0;
}

MyApp::~MyApp() {
	m_socket = 0;
}


TypeId MyApp::GetTypeId(void) {
	static TypeId tid = TypeId("MyApp")
	.SetParent<Application>()
	.SetGroupName("Tutorial")
	.AddConstructor<MyApp>()
	;
	return tid;
}

void MyApp::Setup(Ptr<Socket> socket, Address address, uint32_t packetSize, DataRate dataRate) {
	m_socket = socket;
	m_peer = address;
	m_packetSize = packetSize;
	m_dataRate = dataRate;
}

void MyApp::StartApplication(void) {
	m_running = true;
	m_packetsSent = 0;
	if(InetSocketAddress::IsMatchingType(m_peer)) {
		m_socket->Bind();
	}
	else {
		m_socket->Bind6();
	}
	m_socket->Connect(m_peer);
	SendPacket();
}

void MyApp::StopApplication(void) {
	m_running = false;
	if(m_sendEvent.IsRunning()) {
		Simulator::Cancel(m_sendEvent);
	}
	if(m_socket) {
		m_socket->Close();
	}
}

void MyApp::SendPacket(void) {
	Ptr<Packet> packet = Create<Packet>(m_packetSize);
	m_socket->Send(packet);
	++ m_packetsSent;
	ScheduleTx();
}

void MyApp::ScheduleTx(void) {
	if(m_running) {
		Time tNext(Seconds(m_packetSize * 8 / static_cast<double>(m_dataRate.GetBitRate())));
		m_sendEvent = Simulator::Schedule(tNext, &MyApp::SendPacket, this);
	}
}

static void CwndChange(std::fstream* file, uint32_t oldCwnd, uint32_t newCwnd) {
	// write data (time and window size) to file
	*file << Simulator::Now().GetSeconds() << "," << oldCwnd << "," << newCwnd << std::endl;
}

static void RxDrop(int* dropCount, Ptr<const Packet> p) {
	// increment packet drop count
	std::string str = p->ToString();
	int len = str.size();
	size_t index = str.find("ns3::TcpHeader");
	// find port number
	int portIndex = -1;
	for(int i = index; i < len; i ++) {
		if(str[i] == '>') {
			portIndex = i + 2;
			break;
		}
	}
	std::string temp = "";
	for(int i = portIndex; i < len; i ++) {
		if(str[i] == ' ') {
			break;
		}
		else {
			temp += str[i];
		}
	}
	int portNumber = std::stoi(temp);
	if(portNumber == 8000) {
		(*dropCount) ++;
	}
	else if(portNumber == 9000) {
		(*(dropCount + 1)) ++;
	}
	else if(portNumber == 10000) {
		(*(dropCount + 2)) ++;
	}
}


int main(int argc, char** argv) {
	// enable packet printing for sniffing
	Packet::EnablePrinting();
	
	// default configuration
	int config = 1;

	// parse command-line arguments	
	CommandLine cmd;
	cmd.AddValue("config", "Network Configuration to use (1-3)", config);
	cmd.Parse(argc, argv);
	
	// NODE SETUP

	// create three nodes, N1, N2, N3
	NodeContainer nodes;
	nodes.Create(3);

	// LINK-LAYER

	// set-up 2 point-to-point links (N1-N3 and N2-N3)
	PointToPointHelper link13, link23;
	link13.SetDeviceAttribute("DataRate", StringValue("10Mbps"));
	link13.SetChannelAttribute("Delay", StringValue("3ms"));
	link23.SetDeviceAttribute("DataRate", StringValue("9Mbps"));
	link23.SetChannelAttribute("Delay", StringValue("3ms"));

	// install link between N1 and N3
	NetDeviceContainer netDevices13 = link13.Install(nodes.Get(0), nodes.Get(2));
	// install link between N2 and N3
	NetDeviceContainer netDevices23 = link23.Install(nodes.Get(1), nodes.Get(2));

	// set RateErrorModel on sink node
	Ptr<RateErrorModel> errorModel13 = CreateObject<RateErrorModel>(), errorModel23 = CreateObject<RateErrorModel>();
	errorModel13->SetRate(double(0.00001));
	errorModel23->SetRate(double(0.00001));
	// // set model on both receiving devices
	// netDevices13.Get(1)->SetAttribute("ReceiveErrorModel", PointerValue(errorModel13));
	// netDevices23.Get(1)->SetAttribute("ReceiveErrorModel", PointerValue(errorModel23));

	// install default protocol stacks on all nodes
	InternetStackHelper internetStack;
	internetStack.Install(nodes);
	// set model on both receiving devices
	netDevices13.Get(1)->SetAttribute("ReceiveErrorModel", PointerValue(errorModel13));
	netDevices23.Get(1)->SetAttribute("ReceiveErrorModel", PointerValue(errorModel23));
	// NETWORK-LAYER

	// assign IP addresses (both networks are capable of at most 2 nodes)
	Ipv4AddressHelper ipAddress1, ipAddress2;
    ipAddress1.SetBase("10.1.1.0", "255.255.255.252");
    ipAddress2.SetBase("10.1.2.0", "255.255.255.252");
    // store the device interfaces (after assigning IP address)
    Ipv4InterfaceContainer interfaces13 = ipAddress1.Assign(netDevices13);
    Ipv4InterfaceContainer interfaces23 = ipAddress2.Assign(netDevices23);

    // APPLICATION & TRANSPORT LAYER

    // port number for three connections (arbitrary)
    int portNumber1 = 8000, portNumber2 = 9000, portNumber3 = 10000;

    // create tcp packet sink at node 3 (index 2), for connection 1
    PacketSinkHelper sink1("ns3::TcpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), portNumber1));
    ApplicationContainer sinkApps1 = sink1.Install(nodes.Get(2));
    // set start and end time
    sinkApps1.Start(Seconds(1));
    sinkApps1.Stop(Seconds(20));
    // create tcp packet sink at node 3 (index 2), for connection 2
    PacketSinkHelper sink2("ns3::TcpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), portNumber2));
    ApplicationContainer sinkApps2 = sink2.Install(nodes.Get(2));
    // set start and end time
    sinkApps2.Start(Seconds(5));
    sinkApps2.Stop(Seconds(25));
    // create tcp packet sink at node 3 (index 2), for connection 3
    PacketSinkHelper sink3("ns3::TcpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), portNumber3));
    ApplicationContainer sinkApps3 = sink3.Install(nodes.Get(2));
    // set start and end time
    sinkApps3.Start(Seconds(15));
    sinkApps3.Stop(Seconds(30));

    // create tcp packet source at node 1 (index 0)
    // create tcp socket at sender for connection 1 (TcpNewReno for config 1 and 2, TcpNewRenoCSE for config 3)
    Ptr<Socket> tcpSocket1 = nullptr;
    if(config == 3) {
    	TypeId tid = TypeId::LookupByName("ns3::TcpNewRenoCSE");
		std::stringstream nodeId;
		nodeId << nodes.Get(0)->GetId();
		std::string specificNode = "/NodeList/" + nodeId.str() + "/$ns3::TcpL4Protocol/SocketType";
		Config::Set(specificNode, TypeIdValue(tid));
		tcpSocket1 = Socket::CreateSocket(nodes.Get(0), TcpSocketFactory::GetTypeId());
    }
    else {
    	TypeId tid = TypeId::LookupByName("ns3::TcpNewReno");
		std::stringstream nodeId;
		nodeId << nodes.Get(0)->GetId();
		std::string specificNode = "/NodeList/" + nodeId.str() + "/$ns3::TcpL4Protocol/SocketType";
		Config::Set(specificNode, TypeIdValue(tid));
    	tcpSocket1 = Socket::CreateSocket(nodes.Get(0), TcpSocketFactory::GetTypeId());
    }
    // set recipient address for connection 1
    Address recpAddress1(InetSocketAddress(interfaces13.GetAddress(1), portNumber1));
    // create application for connection 1
    Ptr<MyApp> app1 = CreateObject<MyApp>();
    app1->Setup(tcpSocket1, recpAddress1, 3000, DataRate("1500Kbps"));
    // add application on node 1 (index 0)
    nodes.Get(0)->AddApplication(app1);
    // set start and end time
    app1->SetStartTime(Seconds(1));
    app1->SetStopTime(Seconds(20));
    // create tcp socket at sender for connection 2
    Ptr<Socket> tcpSocket2 = nullptr;
    if(config == 3) {
    	TypeId tid = TypeId::LookupByName("ns3::TcpNewRenoCSE");
		std::stringstream nodeId;
		nodeId << nodes.Get(0)->GetId();
		std::string specificNode = "/NodeList/" + nodeId.str() + "/$ns3::TcpL4Protocol/SocketType";
		Config::Set(specificNode, TypeIdValue(tid));
		tcpSocket2 = Socket::CreateSocket(nodes.Get(0), TcpSocketFactory::GetTypeId());
    }
    else {
    	TypeId tid = TypeId::LookupByName("ns3::TcpNewReno");
		std::stringstream nodeId;
		nodeId << nodes.Get(0)->GetId ();
		std::string specificNode = "/NodeList/" + nodeId.str() + "/$ns3::TcpL4Protocol/SocketType";
		Config::Set(specificNode, TypeIdValue(tid));
    	tcpSocket2 = Socket::CreateSocket(nodes.Get(0), TcpSocketFactory::GetTypeId());
    }
    // set recipient address for connection 2
    Address recpAddress2(InetSocketAddress(interfaces13.GetAddress(1), portNumber2));
    // create application for connection 2
    Ptr<MyApp> app2 = CreateObject<MyApp>();
    app2->Setup(tcpSocket2, recpAddress2, 3000, DataRate("1500Kbps"));
    // add application on node 1 (index 0)
    nodes.Get(0)->AddApplication(app2);
    // set start and end time
    app2->SetStartTime(Seconds(5));
    app2->SetStopTime(Seconds(25));
    // create tcp packet source at node 2 (index 1)
    Ptr<Socket> tcpSocket3 = nullptr;
    if(config != 1) {
    	TypeId tid = TypeId::LookupByName("ns3::TcpNewRenoCSE");
		std::stringstream nodeId;
		nodeId << nodes.Get(1)->GetId();
		std::string specificNode = "/NodeList/" + nodeId.str() + "/$ns3::TcpL4Protocol/SocketType";
		Config::Set(specificNode, TypeIdValue(tid));
		tcpSocket3 = Socket::CreateSocket(nodes.Get(1), TcpSocketFactory::GetTypeId());
    }
    else {
    	TypeId tid = TypeId::LookupByName("ns3::TcpNewReno");
		std::stringstream nodeId;
		nodeId << nodes.Get(1)->GetId();
		std::string specificNode = "/NodeList/" + nodeId.str() + "/$ns3::TcpL4Protocol/SocketType";
		Config::Set(specificNode, TypeIdValue(tid));
    	tcpSocket3 = Socket::CreateSocket(nodes.Get(1), TcpSocketFactory::GetTypeId());
    }
    // set recipient address for connection 3
    Address recpAddress3(InetSocketAddress(interfaces23.GetAddress(1), portNumber3));
    // create application for connection 3
    Ptr<MyApp> app3 = CreateObject<MyApp>();
    app3->Setup(tcpSocket3, recpAddress3, 3000, DataRate("1500Kbps"));
    // add application on node 2 (index 1)
    nodes.Get(1)->AddApplication(app3);
    // set start and end time
    app3->SetStartTime(Seconds(15));
    app3->SetStopTime(Seconds(30));

   	// create file to store cwnd data (sender's side)
   	std::fstream file1("connection1config" + std::to_string(config) + ".csv", std::ios::out), file2("connection2config" + std::to_string(config) + ".csv", std::ios::out), file3("connection3config" + std::to_string(config) + ".csv", std::ios::out);
  	tcpSocket1->TraceConnectWithoutContext("CongestionWindow", MakeBoundCallback(&CwndChange, &file1));
  	tcpSocket2->TraceConnectWithoutContext("CongestionWindow", MakeBoundCallback(&CwndChange, &file2));
  	tcpSocket3->TraceConnectWithoutContext("CongestionWindow", MakeBoundCallback(&CwndChange, &file3));

	// count packet drops (done from receiver's side)  
	int dropCount[] = {0, 0, 0};
	netDevices13.Get(1)->TraceConnectWithoutContext("PhyRxDrop", MakeBoundCallback(&RxDrop, dropCount));
	netDevices23.Get(1)->TraceConnectWithoutContext("PhyRxDrop", MakeBoundCallback(&RxDrop, dropCount));
	
	// stop simulation at t=30 seconds
    Simulator::Stop(Seconds(30));
  	// run simulation
  	Simulator::Run();
  	// destroy and deallocate resources
  	Simulator::Destroy();
  	std::cout << "Number of packets dropped on Connection 1: " << dropCount[0] << std::endl;
  	std::cout << "Number of packets dropped on Connection 2: " << dropCount[1] << std::endl;
  	std::cout << "Number of packets dropped on Connection 3: " << dropCount[2] << std::endl;
}