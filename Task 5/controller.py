'''
Please add your name:
Please add your matric number: 
'''

import sys
import os
from sets import Set

from pox.core import core

import pox.openflow.libopenflow_01 as of
import pox.openflow.discovery
import pox.openflow.spanning_forest

from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.addresses import IPAddr, EthAddr

log = core.getLogger()

# Constants
# ==== PRIORITY ==== #
PRIORITY_FIREWALL = 100 # Higher has more priority
PRIORITY_QUEUE = 50 
# ==================
# ==== QUEUES ====#
QUEUE_NORM = 2
QUEUE_PREM = 1 
QUEUE_SWITCH = 0
# =================

class ControllerPolicy():
    def __init__(self):
        self.firewall = [] # Array of dictionary
        self.premium = set()
        self.parse()
    
    # Parse the text file
    def parse(self):
        log.debug("+++++++++++++++++++ FIRE WALL POLICIES   +++++++++++++++++++++")
        f = open("policy.in", "r")
        policies = f.read().split()
        log.info(policies)

        num_firewall = int(policies[0])
        num_premium = int(policies[1])
        firewall_policies = policies[2:2 + num_firewall]
        premium_host  = policies[num_firewall + 2 :]
        log.debug("\n\nnum of pre: " + str(num_premium))
        log.debug("\nPre: " + str(premium_host))

        # Parse Firewall
        for x in range(num_firewall):
        # Types of firewall rules
        # 1) IP, Port : Block the TCP traffic sent to a certain host on a certain port
        # 2) IP1, IP2, Port: Block the TCP traffic originating from IP1 to IP2 on port 
            info = firewall_policies[x].split(',')
            policy = {}
            if len(info) == 2: # Type 1
                policy["dst_ip"] = info[0]
                policy["dst_port"] = info[1]
            elif len(info) == 3: # Type 2
                policy["src_ip"] = info[0]
                policy["dst_ip"] = info[1]
                policy["dst_port"] = info[2]
            else:
                log.info("\n +++++++++++++ Error parsing firewall policies! ++++++++++++++++")
            self.firewall.append(policy)
        
        # Parse Premium
        for x in range(num_premium):
            self.premium.add(premium_host[x])


class Controller(EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)
        core.openflow_discovery.addListeners(self)
        self.table = {} # Table to record origins
        # Table looks like this
        # { 
        #   s1_dpid: { src1 : src_port1, src2 : src_port2 }, 
        #   dqid2: { src2 : src_port2 } 
        # }
        self.TTL = 30

        
    # You can write other functions as you need.
        
    def _handle_PacketIn (self, event):    
        log.debug("\n\n ======================== New Arrival ===========================\n")
        packet = event.parsed # Parsed packet data
        packet_in = event.ofp # The actual packet
        src_mac = packet.src # Mac Add of Src
        src_port = event.port
        dest_mac = packet.dst
        dpid = dpid_to_str(event.dpid)
        log.debug("packet: dpid: %s, src: %s, dst: %s, port: %s" % (dpid, src_mac, dest_mac, src_port))


        # install entries to the route table (Create a flow table modification message)
        def install_enqueue(dst_port, qid):
            # Create message
            msg = of.ofp_flow_mod()
            msg.priority = PRIORITY_QUEUE
            msg.match = of.ofp_match.from_packet(packet, src_port)
            msg.data = packet_in
            msg.idle_timeout = self.TTL # Part 3 (Add a TTL to every flow entry)
            msg.hard_timeout = self.TTL # Part 3
            msg.actions.append(of.ofp_action_enqueue(port=dst_port, queue_id=qid)) # Part 5, queue used defined here
            event.connection.send(msg)
            log.debug("S%s: Output data to port %s at queue %d", str(dpid), str(dst_port), qid)

        # When it knows nothing about the destination, flood but don't install the rule
        def flood (message = None):
            # define your message here
            msg = of.ofp_packet_out()
            msg.data = packet_in
            msg.in_port = src_port
            msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
            event.connection.send(msg)
            log.debug("(FLOODING)S%s: Message sent - Outport %s\n: ", str(dpid), str(of.OFPP_FLOOD)) 

                    # ofp_action_output: forwarding packets out of a physical or virtual port
                    # OFPP_FLOOD: output all openflow ports expect the input port and those with 
                    #    flooding disabled via the OFPPC_NO_FLOOD port config bit
                    # msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))

        # Part 5: Get the queue ID based on the srcIP
        def getQid():
            qid = QUEUE_NORM # By default
            srcIP = "" # Init
            if packet.type == packet.IP_TYPE:
                srcIP = packet.payload.srcip
            elif packet.type == packet.ARP_TYPE:
                srcIP = packet.payload.protosrc
            
            log.debug("CURRENT SET:" + str(policies.premium))
            if str(srcIP) in policies.premium:
                log.debug("Found srcIP in premium\n")
                qid = QUEUE_PREM
    
            log.debug("(QUEUE %d set for host at IP %s)" % (qid, srcIP))
            return qid

        # Check the packet and decide how to route the packet
        def forward(message = None):
            # Check if theres no record in the table, we would record it
            if src_mac not in self.table[dpid]: 
                log.debug("(Adding entry into table)S%s: Mac entry %s @Port %s\n: ", str(dpid), str(src_mac), str(src_port)) 
                self.table[dpid][src_mac] = src_port  

            # Grab the dst port required
            if dest_mac not in self.table[dpid]:
                flood()
            else:
                dst_port = self.table[dpid][dest_mac]
                log.info("Found dst port at: " + str(dst_port))
                qid = getQid() # Part 5 here, get queue location
                install_enqueue(dst_port, qid)

        # Main function caller here
        forward()
        log.debug("\n\n ================== END OF ROUTE ==================== \n\n")  

    # This is to handle ttl (PART 3)	
    def _handle_PortStatus(self, event):
        log.debug("==== Noted change in ports ===")
        action = "Modified"
        if event.added:
            action = "Added"
        elif event.deleted:
            action = "Delete"
        
        log.debug("Port %s on Switch %s has been %s." % (event.port, event.dpid, action))	
        # Remove the table in our controller
        self.clear_table()
        # Rely on tts to timeout the rest of the stuff in the switch flow table (Technically can delete but meh)

    # Reset the table (PART 3)
    def clear_table(self):
        log.debug("Dropped controller Mac to Port table")
        new_table = {}
        for key in self.table:
            new_table[key] = {}
        self.table = new_table

    def _handle_ConnectionUp(self, event):
        dpid = dpid_to_str(event.dpid)
        log.debug("Switch %s has come up.", dpid)
    
        # init table when switch connects
        self.table[dpid] = {}
        
        # init plans table when switch connects
        self.table[dpid] = {}

        # Send the firewall policies to the switch (PART 4)
        def sendFirewallPolicy(connection, policy):
            # define your message here
            dst_ip = IPAddr(policy.get("dst_ip"))
            dst_port = int(policy.get("dst_port"))
            src_ip = "" #init
        
            msg = of.ofp_flow_mod()
            msg.priority = PRIORITY_FIREWALL
        
            # Firewall matching here
            block = of.ofp_match(dl_type = 0x0800, nw_proto = 6) # 6 means TCP packets, use 1 for ICMP Packets
            block.tp_dst = int(dst_port) # Destination Port TCP/UDP
            block.nw_dst = IPAddr(dst_ip) # IP dest Address

            if "src_ip" in policy: # TYPE 2
                src_ip = IPAddr(policy.get("src_ip"))
                block.nw_src = src_ip # IP Source Address

            msg.match = block # Assign the firewall matching
            msg.actions.append(of.ofp_action_output(port=of.OFPP_NONE))
            connection.send(msg)
            log.debug("\n Switch %s: (Firewall rule) - src: %s, dest: %s, dest_port: %s", dpid, src_ip, dst_ip, dst_port) 
            #     # OFPP_NONE: outputting to nowhere
            #     # msg.actions.append(of.ofp_action_output(port = of.OFPP_NONE))

        # Firewall Policies
        log.debug("\n ===== FIREWALL RULE ========")
        for i in range(len(policies.firewall)):
            sendFirewallPolicy(event.connection, policies.firewall[i])
        log.debug("\n\n ==========")

        # Premium Policies
        log.debug("\n === Showing Premium Policies ====\n")
        for x in policies.premium:
            log.debug("Installing Premium for host at %s" % (x))
        log.debug("===============\n")

# For declaring policies
policies = ControllerPolicy() 

def launch():
    # Run discovery and spanning tree modules
    pox.openflow.discovery.launch()
    pox.openflow.spanning_forest.launch()

    # Starting the controller module
    core.registerNew(Controller)
