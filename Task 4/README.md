# Task 5 - Install Premium Queue

## Topology
We can only declare queues at the ports of switches. Mininet api gave us a handy api to get all the different links:

```python
    for link in topo.links(sort=True,withKeys=False, withInfo=True):
    	print(link)
```

We can make use of that to find all the links noted by the black dots:
![Switch Image](https://deunitato.github.io/NUSCSMODS/img/CS4226_task5_2.png)

In order to make it easier to retrieve the bandwidth, we would process the infomation retrieved from the input file in 
the data structure `info` where `info[n1][n2]` would denote the bandwidth of the link between `n1` and `n2`

### Code changes

1. Creating 3 queues for each link

```python
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
```

> Note that you cannot create queues for a host port, this code does not do the check for it so you could do your own changes (winks*)

Explain:
- `queues=0=@q0,1=@q1,2=@q2` in the queue code means that you are creating 3 queues `q0`, `q1` and `q2` with the id `0`, `1` and `2` respectively
We can use this to infer in our controller code.
- `-- --id=@q0 create queue other-config:max-rate=%i other-config:min-rate=%i \` sets `q0` with the respective max and minrate. Here we set it to be the default 10Mbits / 100Mbits

2. Assigning each link

As explained at the beginning, we could make use of mininet's provided api to get the links. Here we have to do both direction in case we are doing a switch to switch link.

```python
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
``` 


## Controller
Choice of queues is done during flow table population. In order

### Code Changes
1. Check for queue to be used, refer to the pdf. The idea is to give the premium based on the srcIP

```python
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
```

2. Enqueue it in the `install_enqueue` function using the following

```python
	msg.actions.append(of.ofp_action_enqueue(port=dst_port, queue_id=qid)) # Part 5, queue used defined here
```



