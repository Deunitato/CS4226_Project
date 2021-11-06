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
        self.table = {}
        # Table looks like this
        # { src : src_port}
        
        
    def _handle_PacketIn (self, event):    
      ## HELPER FUNCTIONS
        def install_enqueue(event, packet, packet_in):
          src_mac = str(packet.src)
          src_port = str(packet_in.in_port)
          log.info("\nAdding the following into flow table:\n")
          log.info("      " + src_mac + " : " + str(src_port))
	    
    	  # Check the packet and decide how to route the packet
        def forward(message = None):
          event.connection.send(msg)

        # When it knows nothing about the destination, flood the entire surrounding network
        def flood (message = None):
          # define your message here
          dpid = event.dpid
          msg = of.ofp_flow_mod()
          msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
          log.info("(FLOODING)S%i: Message sent - Outport %i\n: ", dpid, of.OFPP_FLOOD) 
          event.connection.send(msg)

            # ofp_action_output: forwarding packets out of a physical or virtual port
            # OFPP_FLOOD: output all openflow ports expect the input port and those with 
            #    flooding disabled via the OFPPC_NO_FLOOD port config bit
            # msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
      
      # MAIN CODE
      packet = event.parsed # Parsed packet data
      packet_in = event.ofp # The actual packet

      # Check if theres a record in the table
      if packet.src not in self.table: 
        install_enqueue(event, packet, packet_in)

      # Grab the dst port required
      if packet.dst in self.table:
              dst_port = self.table.get(packet.dst)
        log.info("\nFound dst port at: " + str(dst_port))
        # Create message
        msg = of.ofp_flow_mod()
        msg.match.d1_src = packet.src
        msg.match.d1_dst = packet.dst
        msg.actions.append(of.ofp_action_output(port=dst_port))

        forward(msg)
      else: # Since we don't know, just flood all our ports
        flood()



    def _handle_ConnectionUp(self, event):
        dpid = dpid_to_str(event.dpid)
        log.debug("Switch %s has come up.", dpid)
        
        
        # Send the firewall policies to the switch
        # def sendFirewallPolicy(connection, policy):
        #     # define your message here
            
        #     # OFPP_NONE: outputting to nowhere
        #     # msg.actions.append(of.ofp_action_output(port = of.OFPP_NONE))

        # for i in [FIREWALL POLICIES]:
        #     sendFirewallPolicy(event.connection, i)
    


def launch():
    # Run discovery and spanning tree modules
    pox.openflow.discovery.launch()
    pox.openflow.spanning_forest.launch()

    # Starting the controller module
    core.registerNew(Controller)
