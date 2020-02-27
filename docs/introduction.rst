Introduction
============

EMANE-Docker is a platform to deploy and emulate distributed wireless networks using
`EMANE (Extendable Module Ad-hoc Network Emulator) <https://github.com/adjacentlink/emane>`_.
EMANE-Docker allows you to deploy arbitrary topologies with different routing protocols including OLSR,
OLSRv2 and OSPF, test different traffic loads (with MGEN and iPerf) and network events with EMANE Event Generator.

EMANE-Docker can do the following:

* Deploy a wireless network, where each node is emulated with a Docker container
* Connect each node base on the initial topology using EMANE
* Run EMANE EventService to emulate network events
* Generate traffic between nodes using MGEN or iPerf


The following shows the parameters of the EMANE-Docker platform.



usage: emane-docker [-h] [-s] [-S] [-y] [-c CONFIG_FILE] [-t TOPOLOGY_FILE]
                    [-v] [--no-cli] [--no-log] [--debug] [--draw-topology]
                    [--figure-path FIGURE_PATH]

optional arguments:
  -h, --help            show this help message and exit
  -s, --start           run EMANE-Docker
  -S, --stop            stop EMANE-Docker
  -y                    answer yes to all prompts
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        path for configuration file
  -t TOPOLOGY_FILE, --topology-file TOPOLOGY_FILE
                        path to the topology file, overrides he path in
                        configuration file
  -v, --version         show program's version number and exit
  --no-cli              do not run EMANE-Docker CLI
  --no-log              do not output logs
  --debug               set log level to debug
  --draw-topology       draw current topology file
  --figure-path FIGURE_PATH
                        output path for figure, if --draw-topology is
                        specified