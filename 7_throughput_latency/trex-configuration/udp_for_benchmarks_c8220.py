# c8220 single-port traffic profile -- same-IP convention (matches xl170).
# Single real 10GbE port (82:00.0/enp130s0f0) + dummy second port.
# src=dst=10.10.1.2 so T-Rex sends to DUT (10.10.1.1) via port 0 and
# receives the forwarded packets back on the same port.
#
# Modified from trex, to also vary UDP dport when running multiple streams
from trex_stl_lib.api import *
class STLS1(object):
    '''
    Generalization of udp_1pkt_simple, can specify number of streams and packet length
    '''
    def create_stream (self, packet_len, stream_count):
        packets = []
        for i in range(stream_count):
            base_pkt = Ether()/IP(src="10.10.1.2",dst="10.10.1.2")/UDP(dport=12+i,sport=1025)
            base_pkt_len = len(base_pkt)
            base_pkt /= 'x' * max(0, packet_len - base_pkt_len)
            packets.append(STLStream(
                packet = STLPktBuilder(pkt = base_pkt),
                mode = STLTXCont()
            ))
            if i == 0: # add latency stream
                packets.append(STLStream(
                    packet = STLPktBuilder(pkt = base_pkt),
                    mode = STLTXCont(pps=1000),
                    flow_stats = STLFlowLatencyStats(pg_id = stream_count + 1)
                ))
        return packets
    def get_streams (self, direction = 0, packet_len = 64, stream_count = 1, **kwargs):
        return self.create_stream(packet_len - 4, stream_count)
def register():
    return STLS1()
