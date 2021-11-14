# Task 4 - Fault Tolerance


## Controller
In order to ensure theres fault tolerance, the PDF suggested that we would have to ensure that flow entrys installed in the switches
comes with a TTL, time to live. Here we set the TTL to be 30.
It also worth nothing that if the flow table entry have a TTL, we would also need to change our mac to port table in our 
controller as well. Since the topology changed, we would want to erased the previous records and repopulate the entire table with the correct entry.


### Code Changes
1. Add a TTL to the flow entry
We made the following changes to our `install_enqueue` function 
```python
	msg = of.ofp_flow_mod()
	msg.match = of.ofp_match.from_packet(packet, src_port)
	msg.data = packet_in
	msg.idle_timeout = self.TTL # Part 3 (Add a TTL to every flow entry)
	msg.hard_timeout = self.TTL # Part 3
	msg.actions.append(of.ofp_action_output(port=dst_port))
	event.connection.send(msg)
```


2. Reset the current table

We should only reset the table when changes were discovered in our topology. Luckily, our controller has an event interrupt that would
trigger when there's a change in the topology detected. This api is called `_handle_PortStatus(self, event)`

```python
	def _handle_PortStatus(self, event):
		# Remove the table in our controller
		self.clear_table()
		# Rely on tts to timeout the rest of the stuff in the switch flow table (Technically can delete but meh)
```


In our clear_table function, we would reset all the records for every switch in the table

```python
    def clear_table(self):
        new_table = {}
        for key in self.table:
            new_table[key] = {}
        self.table = new_table
```


