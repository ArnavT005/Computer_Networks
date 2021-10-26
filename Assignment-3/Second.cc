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
	(*dropCount) ++;
}


int main(int argc, char** argv) {
	// default channel and application data rate (in Mbps)
	double channelDR = 6.0, appDR = 2.0;

	// parse command-line arguments	
	CommandLine cmd;
	cmd.AddValue("channelDR", "Channel Data Rate to use (in Mbps)", channelDR);
	cmd.AddValue("appDR", "Application Data Rate to use (in Mbps)", appDR);
	cmd.Parse(argc, argv);
	
	// set TCP version (NewReno)
	Config::SetDefault("ns3::TcpL4Protocol::SocketType", StringValue("ns3::TcpNewReno"));

	// NODE SETUP

	// create two nodes, N1 and N2
	NodeContainer nodes;
	nodes.Create(2);

	// LINK-LAYER

	// set-up link attributes
	PointToPointHelper link;
	link.SetDeviceAttribute("DataRate", StringValue(std::to_string(static_cast<int>(channelDR)) + "Mbps"));
	link.SetChannelAttribute("Delay", StringValue("3ms"));
	
	// install link between the two nodes
	NetDeviceContainer netDevices;
	netDevices = link.Install(nodes);

	// set RateErrorModel on sink node
	Ptr<RateErrorModel> errorModel = CreateObject<RateErrorModel>();
	errorModel->SetRate(double(0.00001));
	netDevices.Get(1)->SetAttribute("ReceiveErrorModel", PointerValue(errorModel));

	// install protocol stacks on nodes
	InternetStackHelper internetStack;
	internetStack.Install(nodes);

	// NETWORK-LAYER

	// assign IP addresses to the two nodes (subnet with mask 255.255.255.252 can have at most 2 nodes)
	Ipv4AddressHelper ipAddress;
    ipAddress.SetBase("10.1.1.0", "255.255.255.252");
    // store the device interfaces (after assigning IP address)
    Ipv4InterfaceContainer interfaces = ipAddress.Assign(netDevices);

    // APPLICATION & TRANSPORT LAYER

    // application port number (arbitrary)
    int portNumber = 8000;

    // create tcp packet sink at node 2 (index 1)
    PacketSinkHelper sink("ns3::TcpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), portNumber));
    ApplicationContainer sinkApps = sink.Install(nodes.Get(1));
    // set start and end time
    sinkApps.Start(Seconds(1));
    sinkApps.Stop(Seconds(30));

    // create tcp packet source at node 1 (index 0)
    // create tcp socket at sender
    Ptr<Socket> tcpSocket = Socket::CreateSocket(nodes.Get(0), TcpSocketFactory::GetTypeId());
    // set recipient address
    Address recpAddress(InetSocketAddress(interfaces.GetAddress(1), portNumber));
    // create application
    Ptr<MyApp> app = CreateObject<MyApp>();
    app->Setup(tcpSocket, recpAddress, 3000, DataRate(std::to_string(static_cast<int>(appDR * 1000)) + "Kbps"));
    // add application on node 1 (index 0)
    nodes.Get(0)->AddApplication(app);
    // set start and end time
    app->SetStartTime(Seconds(1));
    app->SetStopTime(Seconds(30));

   	// create file to store cwnd data (sender's side)
   	std::fstream file("channel" + std::to_string(static_cast<int>(channelDR)) + "app" + std::to_string(static_cast<int>(appDR * 1000)) + ".csv", std::ios::out);
  	tcpSocket->TraceConnectWithoutContext("CongestionWindow", MakeBoundCallback(&CwndChange, &file));

	// count packet drops (done from receiver's side)  
	int dropCount = 0;
	netDevices.Get(1)->TraceConnectWithoutContext("PhyRxDrop", MakeBoundCallback(&RxDrop, &dropCount));
	
	// stop simulation at t=30 seconds
    Simulator::Stop(Seconds(30));
  	// run simulation
  	Simulator::Run();
  	// destroy and deallocate resources
  	Simulator::Destroy();
  	std::cout << "Number of packets dropped: " << dropCount << std::endl;
  	std::cout << "Number of packets sent: " << app->m_packetsSent << std::endl;
}