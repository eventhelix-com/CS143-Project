import Queue

class PacketTracker:
    """Tracks the packets that have been received before a packet with a
       smaller id, and keeps track of the packet with the smallest id number
       that is expected next.
    
    Attributes:
        next_packet: Next expected packet
        early_packets: Queue of packets that arrived before packets with smaller
            id numbers
    """

    def __init__(self):
        self.next_packet = 0
        self.early_packets = Queue.PriorityQueue()

    # Called by flow when an acknowledgement has been received
    def account_for_packet(self, packet_id):
        # The acknowledgement we just received is for the packet that 
        # we were expecting, so update the next packet
        if packet_id == self.next_packet:
            self.next_packet += 1
            # If our new next packet has already been received (in the early 
            # packets queue), we want to find the subsequent packet that hasn't 
            # been received yet
            while not self.early_packets.empty() and self.next_packet == self.early_packets.queue[0]:
                self.next_packet += 1
                self.early_packets.get_nowait()
        # Packet of larger id arrived before the next packet we were expecting
        elif packet_id > self.next_packet:
            self.early_packets.put(packet_id)
        else:
            pass
            #received packet again - do nothing
            
    def total_count_received(self):
        return self.next_packet + len(self.early_packets.queue)
