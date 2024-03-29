# include <math.h>
#include "TcpNewRenoCSE.h"
#include "ns3/log.h"

namespace ns3 {
NS_LOG_COMPONENT_DEFINE ("TcpNewRenoCSE");
NS_OBJECT_ENSURE_REGISTERED (TcpNewRenoCSE);

TypeId
TcpNewRenoCSE::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::TcpNewRenoCSE")
    .SetParent<TcpNewReno> ()
    .AddConstructor<TcpNewRenoCSE> ()
    .SetGroupName ("Internet")
  ;
  return tid;
}

TcpNewRenoCSE::TcpNewRenoCSE (void) : TcpNewReno ()
{
  NS_LOG_FUNCTION (this);
}

TcpNewRenoCSE::TcpNewRenoCSE (const TcpNewRenoCSE& sock)
  : TcpNewReno (sock)
{
  NS_LOG_FUNCTION (this);
}

TcpNewRenoCSE::~TcpNewRenoCSE (void)
{
  NS_LOG_FUNCTION (this);
}


uint32_t
TcpNewRenoCSE::SlowStart (Ptr<TcpSocketState> tcb, uint32_t segmentsAcked)
{
  NS_LOG_FUNCTION (this << tcb << segmentsAcked);

  if (segmentsAcked >= 1)
    {
      tcb->m_cWnd += static_cast<uint32_t>(pow(tcb->m_segmentSize, 1.9) / tcb->m_cWnd.Get());
      NS_LOG_INFO ("In SlowStart, updated to cwnd " << tcb->m_cWnd << " ssthresh " << tcb->m_ssThresh);
      return segmentsAcked - 1;
    }

  return 0;
}

void
TcpNewRenoCSE::CongestionAvoidance (Ptr<TcpSocketState> tcb, uint32_t segmentsAcked)
{
  NS_LOG_FUNCTION (this << tcb << segmentsAcked);

  if (segmentsAcked > 0)
    {
      tcb->m_cWnd += static_cast<uint32_t> (0.5 * tcb->m_segmentSize);
      NS_LOG_INFO ("In CongAvoid, updated to cwnd " << tcb->m_cWnd << " ssthresh " << tcb->m_ssThresh);
    }
}

std::string
TcpNewRenoCSE::GetName () const
{
  return "TcpNewRenoCSE";
}


Ptr<TcpCongestionOps>
TcpNewRenoCSE::Fork ()
{
  return CopyObject<TcpNewRenoCSE> (this);
}

} // namespace ns3
