#!/usr/bin/env python

import numpy as np

from emane_docker.constant import Constant
from emane_docker.log import LOG
from emane_docker.distribution import DistributionParser


class TrafficGenerator:
    def __init__(self, nodes, containers, traffic_config, generate_configurations, duration):
        self.nodes = nodes
        self.containers = containers
        self.duration = duration
        self.traffic_config = traffic_config
        self.generate_configurations = generate_configurations
        self.arrival_distribution = DistributionParser(distribution=traffic_config['arrival'])
        self.bandwidth_distribution = DistributionParser(distribution=traffic_config['bandwidth'])
        self.flow_size_distribution = DistributionParser(distribution=traffic_config['flow_size'])
        self.flow_size_distribution.start_next_simulation()

    def _is_server_node(self, node_id):
        return node_id % 2 == 0  # Even number: server, odd number: client

    def _pick_destination_ip(self, node_id):
        dest_node_id = node_id
        while dest_node_id == node_id or not self._is_server_node(dest_node_id):
            dest_node_id = np.random.randint(1, len(self.nodes) + 1)
        return '10.100.0.%d' % dest_node_id

    def start(self):
        flow_id = 0
        for node in self.nodes:
            with open('%s/%s/mgen.in' % (Constant.CP_CONFIG_DIRECTORY, node), 'w') as f:
                node_id = int(node.split('-')[1])
                # If the node is server, listen at TCP port 5001
                if self._is_server_node(node_id):
                    # f.write('0.0 LISTEN TCP 5001\n%.2f IGNORE TCP 5001\n' % self.duration)
                    f.write('0.0 LISTEN UDP 5001\n%.2f IGNORE UDP 5001\n' % (
                        self.duration * (self.arrival_distribution.num_simulations + 1)))
                    continue
                # Otherwise, generate flows
                self.arrival_distribution.rewind()
                current_time = 0
                while self.arrival_distribution.start_next_simulation():
                    simulation_time = 0.0
                    while True:
                        bandwidth = self.bandwidth_distribution.get_next()
                        flow_id += 1
                        next_event_time = self.arrival_distribution.get_next()
                        # sleep(next_event_time)
                        current_time += next_event_time
                        simulation_time += next_event_time
                        if simulation_time > self.duration:
                            break
                        # bw in kbps, 600 bytes packet size
                        rate = int(bandwidth * 1024.0 / 600 / 8)
                        f.write('%.2f ON %d UDP SRC 5001 DST %s/5001 PERIODIC [%d %d]\n' % (
                            current_time, flow_id,
                            self._pick_destination_ip(node_id=node_id), rate,
                            600))
                        stop_time = 1024 * self.flow_size_distribution.get_next() / (rate * 600)
                        f.write('%.2f OFF %d\n' % (current_time + stop_time, flow_id))

                        # pkt_size = self.flow_size_distribution.get_next() * 1024
                        # f.write('%.2f ON %d TCP SRC 5001 DST %s/5001 PERIODIC [1 %d] COUNT 1\n'
                        # % (
                        #     current_time, flow_id,
                        #     self._pick_destination_ip(node_id=node_id), int(pkt_size)))

        LOG.debug('Traffic generator configurations are generated.')

        if not self.generate_configurations:
            for node in self.nodes:
                self.containers[node].exec_run(
                    'mgen input /etc/quagga/mgen.in output /etc/quagga/mgen.out', detach=True)

            LOG.info('Traffic generator is started.')
