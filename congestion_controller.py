import sys
slow_start = "Slow Start"
congestion_avoidance = "Congestion Avoidance"
fast_recovery = "Fast Recovery"


class CongestionController:
    """Implements Congestion Control

    Attributes:
        ssthresh: Slow Start Threshold
        cwnd: Congestion Window Size

    """
    def __init__(self):
        self.ssthresh = 1200
        self.cwnd = 1.0
        self.not_acknowledged = dict()
        self.duplicate_count = 0
        self.next_packet_num = 0
        self.last_ack_received = -1
        self.flow = None

    def acknowledgement_received(self, packet):
        sys.exit("Abstract method acknowledgement_received not implemented")

    def send_packet():
        sys.exit("Abstract method send_packet not implemented")
        
    def wake(self):
        pass
        
class CongestionControllerReno(CongestionController):
    """Implements TCP Reno

    Attributes:
        duplicate_count: Number of duplicate ACKS
    """

    def __init__(self):
        CongestionController.__init__(self)
        self.state = slow_start

    def acknowledgement_received(self, packet):
        if self.state == slow_start:
            self.cwnd += 1
            if self.cwnd > self.ssthresh:
                self.state = congestion_avoidance
        elif self.state == congestion_avoidance:
            if self.next_packet_num == packet.identifier:
                self.cwnd += 1 / self.cwnd
            else:
                self.duplicate_count += 1
                if self.duplicate_count >= 3:
                    self.cwnd /= 2
                    self.ssthresh = self.cwnd
                    self.send_packet()
                    self.state = fast_recovery
        else:
            self.state = congestion_avoidance
            self.cwnd = self.ssthresh
            
    def send_packet():
        pass

    def __str__(self):
        return ("ssthresh:    " + str(self.ssthresh) + "\n"
                "cwnd:        " + str(self.cwnd) + "\n"
                "duplicate ACKS" + str(self.duplicate_count) + "\n")

class CongestionControllerFast(CongestionController):
    """Implements TCP Fast

    Attributes:
        alpha:
    """

    def __init__(self):
        CongestionController.__init__(self)
        self.alpha = 10.0
        self.base_RTT = -1
    
    def acknowledgement_received(self, packet):
        del self.not_acknowledged[packet.identifier]
        
        if self.last_ack_received == packet.next_id:
            self.duplicate_count += 1
            if duplicate_count >= 3:
                send_packet() #TODO mark what packet to send
        rtt = self.clock.current_time - self.not_acknowledged[packet.identifier]
        if self.base_RTT == -1:
            self.base_RTT = rtt
        self.cwnd = self.cwnd * self.base_RTT / rtt
        
        if rtt < self.base_RTT:
            self.base_RTT = rtt

    def acknowledgement_received(self, packet):
        pass

    def send_packet():
        pass

    def __str__(self):
        return ("ssthresh:    " + str(self.ssthresh) + "\n"
                "cwnd:        " + str(self.cwnd) + "\n"
                "alpha:    " + str(self.alpha) + "\n")
