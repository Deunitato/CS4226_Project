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
		def install_enqueue(dst_port):
			# Create message
			msg = of.ofp_flow_mod()
			msg.match = of.ofp_match.from_packet(packet, src_port)
			msg.data = packet_in
			msg.actions.append(of.ofp_action_output(port=dst_port))
			event.connection.send(msg)
 			log.debug("Inserting flow for: " + msg.__str__() + "\n")
			log.debug("S%s: Output data to port %s", str(dpid), str(dst_port))
					
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
			
		# Check the packet and decide how to route the packet
		def forward(message = None):
			# Check if theres no record in the table, we would record it
			if src_mac not in self.table[dpid]: 
				log.debug("(Adding entry into table)S%s: Mac entry %s @Port %s\n: ", str(dpid), str(src_mac), str(src_port)) 
				self.table[dpid][src_mac] = src_port  
				
			if dest_mac not in self.table[dpid]:
				flood()
			else:	
				dst_port = self.table[dpid][dest_mac]
				log.info("Found dst port at: " + str(dst_port))
				install_enqueue(dst_port)
		forward()
		log.debug("\n\n ================== END OF ROUTE ==================== \n\n")  


	def _handle_ConnectionUp(self, event):
		dpid = dpid_to_str(event.dpid)
		log.debug("Switch %s has come up.", dpid)
		
		# init table when switch connects
		self.table[dpid] = {}

def launch():
    # Run discovery and spanning tree modules
    pox.openflow.discovery.launch()
    pox.openflow.spanning_forest.launch()

    # Starting the controller module
    core.registerNew(Controller)
