# Task 2 - Learning Switch


## Controller
The controller main purpose is to tell newly connected switches what to do when they discover a packet. The controller acts
like a brain for these switches and can install flow entries into the switches to instruct them how to handle, where to forward
packets that were never seen before. With that we need to handle a few things
- New packet arrival
- Old packet arrival

In our implementation of our controller, we would do the following things. When a new switch connects and recieve a unknown packetfrom a host. 
It does not know what to do with the packet thus it would contact the controller.
Since the controller does not know where this switch and its port is located, the controller must tell the switch to first **flood the packet**
and hope that the destination host would respond. While doing so, the controller
can keep track of the src host and src port that send the packet so that future switches that wants to contact this src host does not need
to flood the packet since our controller already knows where it is.

The following shows an example of how our controller table structure looks like:

```python

        table = 
		{ 
           s1_dpid: { src1 : src_port1, src2 : src_port2 }, 
           s2_dqid: { src2 : src_port2 } 
        }
```

Everytime a switch ask the controller where to send the packet, if for that switch, the source address and port does not exist in our table, we would add the entry and flood the network.
That way, if the next packet comes and we do have an entry in our controller table, we do not need to flood the system but just do a table lookup and install the flow entry.

### Code
1. Handling packets

Everytime theres an incoming packet to the controller, it would invoke the function ` _handle_PacketIn (self, event)`. From there, the following values can 
be retrieved.

| Values | Meaning | Example | Example Value (h1 to h4) |
|-------|----|----|----|
| event.parsed | Parsed packet Data| packet | (Object) |
| event.ofp | The actual packet data | packet_in | (Object) |
| event.parsed.src | Mac Address of src | src_mac |  00:00:00:00:00:01 |
| event.parsed.dst | Mac Address of Dst | dest_mac |  00:00:00:00:00:04 | 
| event.port | Incoming Port from Src | src_port | 4 |
| event.dpid | Immediate switch Mac Address | dpid | 00:00:00:00:00:03 |


The following shows the code of how to handle the incoming packets

```python
 def forward(message = None):
	# Check if theres no record in the table, we would record it
	if src_mac not in self.table[dpid]:  
		self.table[dpid][src_mac] = src_port  
		
	if dest_mac not in self.table[dpid]:
		flood()
	else:	
		dst_port = self.table[dpid][dest_mac]
		log.info("Found dst port at: " + str(dst_port))
		install_enqueue(dst_port)
```

Basically, this code would:
 - Check if the srcmac entry is already in the controller table, if its not, record the src mac and src port
 - Check if the dest mac address is in our controller table, if its not, we flood
 - Else we should just send install the flow entry using the port value found in our lookup table

2. Constructing Flood Message

Unlike the installing flow entries, we have to use a specical packet to tell the switch not to install the flooding entriesin our 
switch flow table. This is done using the `ofp_packet_out()` msg packet.
Here we will give the values such as the `src_port` and `data` as shown in the following code.

```python
	def flood (message = None):
		msg = of.ofp_packet_out()
		msg.data = packet_in
		msg.in_port = src_port
		msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
		event.connection.send(msg)
		log.debug("(FLOODING)S%s: Message sent - Outport %s\n: ", str(dpid), str(of.OFPP_FLOOD)) 
```

`msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))` tells the switch that this packet is meant be flooded
in the entire system.

3. Installing flow entries

If lets say we do have previous record in our controller table, we could just install flow entries as normal without
having to flood the entire network. Similiarly to flood packet construction, we need to give details such as the packet infomation
and its output port. The only difference is that we would have to construct matching parameters as well as using a differnet
method, `ofp_flow_mod()` to construct our message. This `ofp_flow_mod()` is different from our flooding as it tells the switch
to persist the entry in their flow table

```python
	def install_enqueue(dst_port):
		msg = of.ofp_flow_mod()
		msg.match = of.ofp_match.from_packet(packet, src_port)
		msg.data = packet_in
		msg.actions.append(of.ofp_action_output(port=dst_port))
		event.connection.send(msg)
		log.debug("Inserting flow for: " + msg.__str__() + "\n")
```

Explain:
- `msg.match = of.ofp_match.from_packet(packet, src_port)` tells the switch that the incoming packet must match the packet destination mac address as well as its sor port in order to be forwarded 
- `msg.actions.append(of.ofp_action_output(port=dst_port))` tells the switch that any packets that matches the above would be forwarded to this dst_port

