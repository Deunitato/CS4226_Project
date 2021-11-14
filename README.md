# CS4226_Project (AY21/22 Sem 1)
This implementation of project runs on python2 and on the fangtooth branch for pox controller.


## Mininet Directory

Place the files in the following directory in your mininet vm
```
/home/mininet/
 | - topology.in
 | - mininetTopo.py
 | - /mininet
 | - /pox
      | - policy.in
      | - /pox
            | - misc
                 | - controller.py
```

## Running 
Open two console.

Console 1 (Pox Controller): Run the following command
```shell
cd pox # Enter pox directory

./pox.py log.level --DEBUG misc.controller
```

Console 2 (mininet topology): Run the following command
```
sudo python mininetTopo.py
```


## Specific configure
By default, mininetTopo.py would look at the controller at `0.0.0.0:6633` and the topology file named `topology.in`. You can customise it by using the following format

```shell
sudo python mininetTopo.py [Name of topofile] [IPaddress (without the port)]
```
> Port is not configurable and always set at `6633`

Reset your mininet each time testing a new instance by running
```shell
sudo mn -c
```


