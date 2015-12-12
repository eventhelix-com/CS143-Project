# Network Simulator

## General Information

The program is a Python implementation of a network simulator that uses discrete-event simulation to quickly and accurately simulate network communication. The simulation does not proceed in real-time, but uses a clock and an event queue to simulate time-based events. The use of event-based simulation allows concurrent events and independent devices to be simulated without any sort of parallel processing. The resulting actions that occur in the simulation, such as packet traversal, are extensively logged. This allows for the assessment of network congestion and related properties after the simulation is complete.

## Invoking the Program

The network simulator can be run via the command line on any system with both Python and matplotlib installed. The program takes the relative file path of the network specification as a required argument. Optional arguments can also be provided, as specified below, to modify the behavior of the program. For example, the default congestion control algorithm is TCP Reno, but an optional argument can be provided to specify FAST TCP.


    python main.py mytestcase.json -f


Upon invocation, the simulation builds the network structure as per the JSON network description, runs the simulation, and displays statistical graphs.

### Command line Arguments
    optional arguments:
    -h, --help       show command line help
    -v, --verbose    print almost every action to stdout
    -r, --reno       use TCP Reno congestion control algorithm (default)
    -f, --fast       use FAST TCP congestion control algorithm
    -n, --no-graphs  don't display graphs upon simulation completion
## Overall Design
### Parsing

The program simulates an arbitrary network of links, routers, hosts, and flows. The network configuration is stored in a JSON file containing a single object with the following properties:


    { "links" : [], "flows" : [], "hosts" : [], "routers" : [] }


Each property contains an array of objects. For example, the “links” property contains an array of link objects, each of which specifies properties such as “delay” and “endpoints”.

After parsing a JSON network configuration file, the program creates instances of corresponding Python classes and an instance of the Simulation class, which manages the network simulation and holds references to all of the instances.

### Simulation

The `Simulation` class creates one shared instance each of the `Logger`, `Clock`, and `EventQueue` classes and injects them into the Links, Flows, Hosts, and Routers created by the parsing code.
It then repeatedly attempts to dequeue and perform `Event`s from the `EventQueue`, until either the queue is empty or all `Flow`s report that they have finished transmitting.

### Flow

`Flow`s keep track of the `Host` they are sending packets from, the `Host` they send packets to, how much data they need to send, and how much data they have left to send. They construct `PayloadPacket`s based on this information and instruct their source `Host` to send them. A `Flow` is notified by its source host when an `AcknowledgementPacket` intended for it is received.

Each `Flow` has an associated `CongestionController` that decides which packets to send, when to send them, and how many to send at once. This encapsulates the TCP congestion control logic, and a `Flow` can use either the TCP Reno or the FAST TCP algorithm depending of which subclass of `CongestionController` is assigned to it. The controller controls how the window size is updated, determines when packets get dropped, and checks off packets as they are acknowledged.

### Packet

Packets represent discrete chunks of data that are communicated across links and can be directed across the network. Each packet must include a `size` attribute which is used to determine factors such as how much `Buffer` space a packet occupies and how long it takes to send on a `Link`. Two major categories of packets exist:

- `RoutingPacket`s are used to communicate dynamic routing information across the network. They encode their source `Host` along with a timestamp indicating when they were dispatched. This information is used by the dynamic routing algorithm to propagate the packet across the network and update `RoutingTable`s.
- `StandardPacket`s are used to model communication between `Host`s on a network. `StandardPacket` is an abstract class that has two concrete subclasses:
  - `PayloadPacket`s are used to simulate a payload over the network. As such, their `size` is set to be much larger than that of other packet types even though they don’t contain actual substantial data. Each `PayloadPacket` is uniquely identified by its `Flow` identifier, its packet sequence number, and its duplicate number.
  - `AcknowledgementPacket`s are used to notify the sender of a `PayloadPacket` that it was properly received. Each `AcknowledgmentPacket` includes similar identifies to a `PayloadPacket` and is associated with a particular `PayloadPacket`.
### Device

`Device` is an abstract base class that defines a type that implements a method `handle_packet`. Additionally, every device should include an `identifier` property and should define `attach_link`. Devices are independent agents on the network that can perform computations and send data over their attached links.

### Host

`Host` is a concrete subclass of `Device` that acts as a network endpoint. When its `handle_packet` method is invoked, `Host` expects that the input be a `StandardPacket`—depending on the subclass, the packet is handled differently:

- If the packet is a `PayloadPacket`, the `Host` must respond with an acknowledgement. For each given `Flow` communicating with a `Host`, it must track the sequence of packet identifiers received with a `PacketTracker` so that it can respond with the sequence number of the next expected packet (for congestion control purposes).
- If the packet is a `AcknowledgmentPacket`, the proper `Flow` associated with this acknowledgment is notified via the `acknowledgement_received` method on `Flow`.


The host additionally has the responsibility of periodically sending out `RoutingPacket`s for dynamic routing purposes. Although this responsibility might seem like one more often associated with routers in the real world, having the host send these packets is a functionally equivalent simplification of having the host-attached routers send these packets.

### Router

`Router` is a concrete subclass of `Device` that routes packets between `Host`s on the network. When its `handle_packet` method is invoked, `Router` first determines what type of `Packet` it has received in order to determine how to handle it:

- If the packet is a `RoutingPacket`, it uses the packet to update its `RoutingTable`, and forwards the packet across the other attached `Link`s if it provided more recent information.
- If the packet is a `StandardPacket`, it uses its `RoutingTable` to determine which `Link` to send the packet over based on the destination `Host`, and then sends it over that `Link`.
### Packet Tracker

`PacketTracker` is a utility used to keep track of which packets in a sequence have been received. It provides an efficient mechanism for tracking the sequence number of the lowest-in-sequence missing packet without keep an array of all packets received thus far. Additionally, `PacketTracker` is useful to keep track of how many packets have been received without double-counting duplicates.

`PacketTracker` is implemented as a counter `next_packet` recording the sequence number of the lowest-in-sequence missing packet and a sorted heap `early_packets` of all packets whose sequence number is greater than `next_packet`. Whenever a packet with sequence number `next_packet` is received, the counter is incremented and the `early_packets` heap is used to skip waiting for any packets that have already been received.

### Link

Network links are the carrier of data between devices. Specifically, a `Link` can be attached to two `Device`s such that data can be transmitted between them. Since links ought to have a limited capacity, the `Link` class uses the `LinkReadyEvent` to wait an appropriate delay between sending each `Packet` as determined by the `Link`s rate and the `Packet`’s size. Further, `Link`s simulate the delay it takes for a packet to reach the other size by scheduling a `PacketArrivalEvent` with an appropriate delay based characteristics of the link.

Unlike real-world links, the `Link` class also contains a `Buffer` that holds `Packet`s that are waiting to send while the link is busy. Normally, one might expect such a buffer to exist on real-world routers and hosts, but as a simplification this buffer is managed by the link. The `Buffer` class is a FIFO queue that holds `Packet`s that are waiting to send in either direction over the link. The `Buffer` has a specified capacity, and it tracks its available space as packets are enqueued and dequeued, dropping `Packet`s when space is insufficient. Additionally, the `Buffer` keeps track of which way a `Packet` is to travel so that it can be delivered to the proper `Device`.

When an attached `Device` requests a `Packet` to be sent over its `Link`, the `Packet` is sent immediately if the `Link` is not currently occupied, otherwise it is placed in the `Buffer` to be sent after all other waiting `Packet`s. On the occasion that the `Link` is very busy and the `Buffer` is full, the `Packet` will be dropped. Since `Link` will place packets in its `Buffer` whenever it is currently sending a `Packet`, regardless of direction, it operates as a half-duplex link.

### Event Queue

The event queue encapsulates the logic of scheduling work that ought to occur a later time in the simulation. `EventQueue` defines methods `schedule_event` and `delay_event` that allow classes such as `Link` and `Flow` to schedule work that ought to happen at a given time or after a given delay. `Event`s can also be canceled by the `cancel_event` method, which marks the given event’s `is_canceled` flag so that it can be skipped on dequeue.

The event queue is a critical component to the discrete event-based simulation in that it allows the effect of many components working independently and concurrently while actually running in a single, serial process. When an event is scheduled, the queue places the event in its backing heap, sorted by scheduling time. When `dequeue_next_event` is called, the event that is scheduled to occur soonest is removed from the heap and returned, and the global time is updated that of the event. The simulation will call `perform` on the event so that it can cause its desired side effects.

### Event

`Event` is an abstract base class that defines what methods to which concrete subclasses ought to respond. Specifically, `Event` defines a method `perform` that contain whatever logic is required to do the unit of work with which the event corresponds.


- `PacketArrivalEvent` corresponds with the arrival of a packet on the opposite end of a link from which it was sent. When performed, this event will notify the respective device that it has arrived across the link, and the device will do whatever work necessary to handle its arrival.
- `LinkReadyEvent` corresponds with a link being available to send another packet from its buffer as the previous packet is done being sent and is currently traveling across the link. When performed, this event will notify the link that it may check send another packet from its buffer.
- `FlowWakeEvent` wakes the flow up for the first time and begins sending packets. An instance of this event is added to the event queue to ensure that a `Flow` wakes up again after it times out even if it doesn’t ever get woken up by an acknowledgement.
- `RoutingUpdateEvent` is a periodic trigger that instructs its associated host to send a routing packet. When performed, the host sends a `RoutingPacket` which propagates through the network, allowing routers to update their routing tables.
### Logging

All elements in the simulation have a reference to the shared instance of the Logger class, and log events as they happen in the simulation. The Logger class has specific hardcoded functions for each type of event logged, and separate arrays that store the logged data of each event type. This approach reduces development flexibility in logging but ensures consistency in logged data and eliminates the chance of typos present in a logging approach where event types are stored as strings.

Depending on the verbosity level specified on the command line, the Logger class also prints certain types of events as they are logged. Printing priorities are set within the functions that log each event type.

Logged data is stored by the Logger class as arrays of dictionaries that contain primitives and pointers to relevant objects. Since Python uses reference counting for memory management and almost all objects created by the simulation are logged at some point, this means that almost no memory will be freed until the simulation and the post hoc statistical analysis has concluded. If the program needed to work with very large simulations, logging could be made more memory efficient by extracting the few needed primitives from the logged objects instead of storing the objects themselves.

### Statistics and Graphing

After the simulation concludes, the Statistics class executes an array of graphing functions, each of which works on the database of actions created by the logger and creates a matplotlib plot. Matplotlib automatically combines and displays these graphs.

In most cases, these functions iterate over the relevant array or arrays of log events, and construct a dictionary that maps flow or device ID’s to an array of (time, metric) tuples. The plot is then constructed from the sets of tuples, each of which is colored differently in the plot and labeled according to the flow or device that it represents.

Some types of log events occur tens of thousands of times per simulation. In order to reduce noise and keep matplotlib from being overwhelmed by the number of points to plot, most data is consolidated into averages on 100ms intervals before being plotted. All the data between 0 and 100ms is averaged and consolidated into one plot point at 50ms, and so on.

## Graphics
### Class Usage Hierachy
![image](https://d2mxuefqeaa7sj.cloudfront.net/s_1A0F52981E7D462F50FC01ACB39F630A3DBD18B7BE664EFBD929EF40DBE989CD_1449823786089_classes.png)
### Include Hierarchy
![image](https://d2mxuefqeaa7sj.cloudfront.net/s_1A0F52981E7D462F50FC01ACB39F630A3DBD18B7BE664EFBD929EF40DBE989CD_1449823811194_packages.png)
## Algorithm Implementation
### Dynamic Routing

At a fixed interval, every host on the network sends a RoutingPacket to the router it’s attached to. The RoutingPacket consists of the host’s identifier and a timestamp of when the packet was originally generated. The router that receives it then checks its internal routing table for that host identifier.

If a) that host identifier is not present in its routing table or b) that host identifier is present in its routing table but the last update had an earlier timestamp, it 1) adds an entry noting that packets destined for that host identifier should be forwarded on the link which received the routing packet and 2) forwards that packet, unchanged, to all of the other routers it’s attached to. Otherwise, it does nothing and discards the packet.

Note that if there are multiple routes from a host to a router, it will receive the same RoutingPacket multiple times, but will only update its routing table the first time it receives it. Obviously, a router will receive a given RoutingPacket first on the link with the shortest path from the host to that router. Since in our simulation it takes the same amount of time for a packet to follow a path in either direction, this will be the shortest path from the router to that host.

If a router receives a packet for which it has not yet determined a path, it drops the packet.


### Congestion Control

The congestion control algorithms that were implemented are TCP Reno and FAST TCP.
In general, the congestion controller keeps track of the next new packet number that still has yet to be sent, a dictionary of sent packets and the time they were sent, the expected packet id of the most recent acknowledgement received, and the window size.

Packets are considered dropped when the time that they have been in the network without receiving its acknowledgement exceeds some timeout length. Since waiting for timeouts can be costly in terms of time, a packet is also considered dropped once the controller receives 3 duplicate acknowledgements for a packet in a row.
Duplicate acknowledgements are simulated by using the Packet Tracker to keep track of the smallest packet number the host is still expecting from that flow. That value is stored in the acknowledgement packet as the next expected packet. Duplicate acknowledgements will share that next expected packet ID.
If there are dropped packets, the controller will go into re-transmit mode and attempt to resend the dropped packets first before sending any new packets.

The flow/congestion controller is woken up whenever an acknowledgement is received. In order to prevent the possibility that a flow might stay asleep forever if it never receives an acknowledgement, every time the flow wakes up, it enqueues a flow wake event to wake it up after a packet’s timeout time has passed. This event is cancelled if it wakes up later due to an acknowledgment.

Window size is updated when an acknowledgement is received or when a packet gets dropped. Window size is halved whenever a packet is dropped. TCP Reno keeps track of which state it is in: Slow Start, Congestion Avoidance, or Fast Recovery. Its window size increases at different speeds depending on which state it is in when it receives an acknowledgement.
FAST TCP updates the window by calculating the RTT of the packet and saving the minimum RTT encountered. The new window size equals the old window size times RTT_min and divided by the packet’s RTT. Some constant alpha is added to it for affect how window size changes over time. Incorrect RTT times due to the possibility of an acknowledgement from a supposedly dropped packet coming in right after the packet is resent is dealt with by differentiating between duplicate packets. The packets have a duplicate number, and the duplicate number of the acknowledgement must match the duplicate number of the packet in the list of unacknowledged packets for the packet to get checked off.

## Analysis
  Graph Results
  Simulation Times
### Theoretical Results
- Test Case 0:
    In this case, there is only one flow running from one host to another. So, this flow uses up all the capacity of link L1, giving a throughput of 10 Mbps.The queueing delay of the flow is now equal to the value of alpha used in the window update rule, divided by the throughput of the flow (in packets/second).  Since flow-generated data packets are 1024 bytes, our throughput is 10240 packets/s, and the value of alpha we have used in our TCP-fast algorithm is 50.0. So, the queueing delay of the flow is 4.9 ms, and the queue length of L1 becomes throughput * queueing delay = 50 packets.
    
- Test Case 1:
    Just like test case 0, there is still only 1 flow, F1, but now there are links L0-L5, instead of just 1 link connecting 2 hosts. There are 2 different branches in this network, the top one consisting of links L0, L1, L3, L5 and the bottom branch has links L0, L2, L4, L5. F1 uses up all the capacity of one of these branches, and averaging the link rates of the links in a branch gives a throughput of 11.25 Mbps, or 11520 packets/s.  Only L0 will have a queue, and the queuing delay equals 4.3 ms. The queue length on L1 is 55 packets.
    
- Test Case 2:
    In this case, there are 3 different flows, F1, F2, and F3, that all interact with each other, and begin at different times. F1 starts at 0.5 seconds, F2 starts at 10 seconds, and F3 starts at 20 seconds. We can now calculate the steady state throughput of each flow, and queueing delay in each link.
      
    Between 0–0.5 seconds, there are no flows in the network.
      
    Then, from 0.5 s - 10 s, there is only flow 1 in the network, so we apply the same reasoning we used to analyze throughput in the previous sections. F1 uses up all the capacity of links L1, L2, L3, resulting in a steady state throughput of 10240 packets/s, and gives the same queue length for L1 as in Test Case 0  (50 packets), with a queueing delay of 4.9 milliseconds. There is no queue on links L2, L3.



    Between 10–20 seconds, flows 1 and 2 share link L1, which becomes the bottleneck. There are no queues on links L2 and L3. Flow F2 knows its minimum round trip time (RTT_min,2) = d2 + 4.9 ms, where d2 is the round trip propagation delay of the flow, and 4.9 ms is the  queueing delay, q1, of a previously started flow, F1. The throughput x2, of flow 2 is equal to a/(q2 - q1), and a/(p1 - q1), where p1 is the queueing delay on link L1. We can also use the fact that x1 + x2 = 10240, to derive that p1 = 0.043 seconds. As a result, we can  see that the queue length of L1 is approximately 440 packets.



    After 20 seconds, flows 1 and 2 share link L1, and flows 1 and 3 share link L3, so these become the bottlenecks. There is no queue on link 2. We can write the RTT_min,3 as d3, the round trip propagation of flow 3, and we know that x3 = alpha / p3 (p3 = queueing delay on L3). Just like in the previous time frame, we can solve an equation to find p1 = 0.034 s, and p3 = 0.029s. The flow rates are x1 = 50/(p1 + p3) = 792 packets/s, and x2 = x3 = 50/p3 = 1724 packets/s. The queue length on L1 is 348 packets, and the queue length on L3 is 297 packets.
### Observed Results
- Test Case 0:
    From our simulation results, we see that the average queue length for L1 is around 40 packets when we run TCP fast, which is similar to the expected queue length of 50 packets.
- Test Case 1:
    For this test case, TCP simulation results show that the average queue length is 59 packets for Link L0, and this is similar compared to the expected length of 55 packets
- Test Case 2:
    From our simulations, we can see the flow rate of F1 sharply decreases with the introduction of flow F2 at time 10s, and then there is a more gradual decrease in flow rate as F3 is introduced at 20s. This is due to the link capacity being divided among the flows. The flow rate of F2 also slightly decreases from its initial rate during the time period between after 20 seconds,This reflects the bottlenecks on links L1 and L3 that develop as multiple flows share the capacity of a single link. This aligns with the theoretical results we expect to see. 
    



## Work Process
### Version Control

During development of the program, git version control was used and GitHub hosted the repository. Contributors created feature branches on their local machines and pushed these branches to the remote repository. Pull requests were submitted and assigned to a reviewer before a feature branch was merged with master. Using code review was beneficial in that many important errors were caught before code made it into the master branch.

### Organizing and Planning

Asana was used as a collaboration platform to outline the roadmap and keep the team on track. Tasks were created for each major feature that was to be developed, and contributors were empowered to build the features that were most interesting to them by assigning the task to themselves. These tasks also served as a central place to brainstorm and take notes about how the feature ought to be implemented. Asana made it easy for the team to keep track of deadlines, split up the work, and communicate about what needs to get done and how.
