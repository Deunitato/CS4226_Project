'''
Please add your name:
Please add your matric number: 
'''

import os
import sys
import atexit
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.link import Link
from mininet.node import RemoteController

net = None

# Documentation at http://mininet.org/api/classmininet_1_1topo_1_1Topo.html#a2ce3428ccdffcf537cc680e3ba05e226
class TreeTopo(Topo):		
    def __init__(self):
        # Initialize topology
        Topo.__init__(self)

    def getContents(self, contents):
        info = {}
        hosts = contents[0]
        switch = contents[1]
        links = contents[2]
        linksInfo = contents[3:]
        for l in linksInfo:
            link = l.split(',')
            c = link[0] #Client
            s = link[1] # Switch
            bw = link[2]

            if c not in info:
                info[c] = {}
            if s not in info:
                info[s] = {}

            info[c][s] = int(bw)
            info[s][c] = int(bw)

        self.linksInfo = info   
        return hosts, switch, links, linksInfo

    def build(self):
        # Read file contents
        default_file = 'topology.in' # Default filename if not found

        if len(sys.argv) > 1:
            default_file = sys.argv[1]
        print("(TOPO BUILDER) Reading from file: " + default_file + "\n")
        
        f = open(default_file,"r")
        contents = f.read().split()
        host, switch, link, linksInfo = self.getContents(contents)
        print("Hosts: " + host)
        print("switch: " + switch)
        print("links: " + link)
        print("linksInfo: " + str(linksInfo))
        # Add switch
        for x in range(1, int(switch) + 1):
            sconfig = {'dpid': "%016x" % x}
            self.addSwitch('s%d' % x, **sconfig)
        # Add hosts
        for y in range(1, int(host) + 1):
            ip = '10.0.0.%d/8' % y
            self.addHost('h%d' % y, ip=ip)

        # Add Links
        for x in range(int(link)):
            info = linksInfo[x].split(',')
            host = info[0]
            switch = info[1]
            bandwidth = int(info[2])
            self.addLink(host, switch)
            

# Run this function for each link
def createQosQueue(bw, switch, port):
    '''
    ###################### QUEUE INFOMATION #######################
    # [q2]: Non prem have a most 5Mb/s (Between switch and host) 
    # [q1]: Premium Queues have at least 8Mb/s (Between switch and host) 
    # [q0]: Switch queues should have the default amount (Between switches) 
    ###############################################################
    '''
    
    bw = 1000000 * bw 
    SWITCH = bw * 1
    X = 0.8 * bw # Prem lower bound
    Y = 0.5 * bw # Norm Upper Bound

    # inteface shld be in form of s(switch_Num)-eth(port)
    # e.g s1-eth1 is the port connecting from h1 to switch 1
    # e.g s3-eth1 is the port connecting from h5 to switch 3, this is because h5 is the first connection on switch 3 (See diagram)
    # Note: You can check this by running the command `net` on mininet
    interface = '%s-eth%s' % (switch, port)
    print('Queues Created for %s:\n' % (interface))
    print('[q0] (Norm) - Max-rate:%d, Min-Rate: %d \n[q1] (Prem)- Min-Rate: %d\n[q2](Non-Prem)- MaxRate: %d\n' % (SWITCH, SWITCH, X, Y))
    # Create QoS Queues
    os.system('sudo ovs-vsctl -- set Port %s qos=@newqos \
                -- --id=@newqos create QoS type=linux-htb other-config:max-rate=%i queues=0=@q0,1=@q1,2=@q2 \
                -- --id=@q0 create queue other-config:max-rate=%i other-config:min-rate=%i \
                -- --id=@q1 create queue other-config:min-rate=%i \
                -- --id=@q2 create queue other-config:max-rate=%i' % (interface, bw, SWITCH, SWITCH, X, Y ))


def assignQueues(topo):
    for link in topo.links(sort=True, withKeys=False, withInfo=True):
        host, switch, info = link
        print("\n(" + host + "---" + switch + "):")
        port_1 = info['port1']
        port_2 = info['port2']

        node_1 = info['node1']
        node_2 = info['node2']
        bw = topo.linksInfo[node_1][node_2]
        print('%s@Port%i is connected with bandwith of %i to %s@Port%i' %(node_1, port_1, bw, node_2, port_2))
        createQosQueue(bw, node_1, port_1)
        createQosQueue(bw, node_2, port_2)

def startNetwork():
    info('** Creating the tree network\n')
    topo = TreeTopo()
    controllerIP = '0.0.0.0'

    if len(sys.argv) > 2:
        controllerIP = sys.argv[2]

    global net
    net = Mininet(topo=topo, link = Link,
                    controller=lambda name: RemoteController(name, ip=controllerIP),
                    listenPort=6633, autoSetMacs=True)

    info('** Starting the network\n')
    net.start()

    # Create Qos Queues
    assignQueues(topo)


    # Create QoS Queues
    # > os.system('sudo ovs-vsctl -- set Port [INTERFACE] qos=@newqos \
    #            -- --id=@newqos create QoS type=linux-htb other-config:max-rate=[LINK SPEED] queues=0=@q0,1=@q1,2=@q2 \
    #            -- --id=@q0 create queue other-config:max-rate=[LINK SPEED] other-config:min-rate=[LINK SPEED] \
    #            -- --id=@q1 create queue other-config:min-rate=[X] \
    #            -- --id=@q2 create queue other-config:max-rate=[Y]')

    info('** Running CLI\n')
    CLI(net)

def stopNetwork():
    if net is not None:
        net.stop()
        # Remove QoS and Queues
        os.system('sudo ovs-vsctl --all destroy Qos')
        os.system('sudo ovs-vsctl --all destroy Queue')



if __name__ == '__main__':
    # Force cleanup on exit by registering a cleanup function
    atexit.register(stopNetwork)


    # Tell mininet to print useful information
    setLogLevel('info')
    startNetwork()
