# Task 4 - Firewall


## Controller
In order to create firewall, we need to do the following task:
- Parse the firewall policies from the `policy.in`
- Insert entry into the flow table that would stay there permanetly for every switch that calls the controller

> Its also noted that the firewall row must be of higher priority compared to the other future entries.


### Code Changes
1. Create a policy class to handle policies, this is useful for the next task as well

```python
class ControllerPolicy():
	def __init__(self):
		self.firewall = [] # Array of dictionary
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
```


2. Insert entry into the flow table that would stay there permanetly for every switch that calls the controller

In this code, we have to keep track of two types of firewall policies.
- Type 1: Dest Port and Dest Address
- Type 2: Dest Port, Dest Address and Src ip

Block any packets that matches these policies

```python
	def sendFirewallPolicy(connection, policy):
		dst_ip = IPAddr(policy.get("dst_ip"))
		dst_port = int(policy.get("dst_port"))
		src_ip = "" #init
	
		msg = of.ofp_flow_mod()
		msg.priority = 100
	
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

```

Explaination:
- `msg.priority = 100` sets it as a high priority. Ensure that the flow entry set in the `install_enqueue` is less than this value
- `block = of.ofp_match(dl_type = 0x0800, nw_proto = 6)` , this is a standard match to check for TCP packets. To check for ICMP packets, we can use `nw_proto=1`
- `msg.actions.append(of.ofp_action_output(port=of.OFPP_NONE))` this would tell the switch to discard the packets

Debug:
Running the command `sh ovs-ofctl dump-flows s1` would let us see the flow table in switch `s1`. Seeing the `action` value be `any` means that the switch would drop
any packet that matches the entry as shown below.
![Entry](https://deunitato.github.io/NUSCSMODS/img/CS4226_task4_2.png)


