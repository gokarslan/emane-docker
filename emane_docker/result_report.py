#!/usr/bin/env python3

from math import ceil, floor

import matplotlib.pyplot as plt
from emane_docker.constant import Constant


class Flow:
    # onstant.
    def __init__(self, flow_id, start_time, flow_type, source, destination, rate):
        self.flow_id = flow_id
        self.start_time = start_time
        self.type = flow_type
        self.source = source
        self.destination = destination
        self.rate = rate * 600 * 8
        self.finish_time = 0
        self.size = 0
        self.seqs = dict()

    def set_finish_time(self, finish_time):
        self.finish_time = finish_time
        self.size = (self.finish_time - self.start_time) * self.rate / 8

    def add_seq(self, seq_id, size):
        self.seqs[seq_id] = size

    def __str__(self):
        if self.seqs.keys():
            recv_seqs = len(self.seqs)  # sum(self.seqs.values())
            total_seqs = max(max(self.seqs.keys()), self.size / 600)  # self.size * 1024 + 1
        else:
            recv_seqs = 0
            total_seqs = -1

        flow_id = 'Flow ID: %d: node-%d -> node-%d\n' % (
            self.flow_id, self.source, self.destination)
        start = '\tStart: %.2f, Finish: %.2f, @%.2f Kbps, Size: %.2f KB\n' % (
            self.start_time, self.finish_time,
            self.rate / 1024.0, self.size / 1024.0)
        recv = '\tRecv Seq/Total Seq: %d/%d = %.2f' % (
            recv_seqs, total_seqs, 1.0 * recv_seqs / total_seqs)
        return flow_id + start + recv


class Report:
    def __init__(self, num_nodes):
        self.flows = dict()
        self.servers = list()
        self.clients = set()
        for node_id in range(1, num_nodes + 1):
            with open('%s/node-%d/mgen.in' % (Constant.CP_CONFIG_DIRECTORY, node_id), 'r') as f:
                for line in f:
                    if 'LISTEN' in line:
                        self.servers.append(node_id)
                        break
                    self.clients.add(node_id)
                    if 'ON' in line:
                        line = line.split()
                        flow_id = int(line[2])
                        destination_id = int(line[7].split('/')[0].split('.')[-1])
                        self.flows[flow_id] = Flow(flow_id=flow_id, start_time=float(line[0]),
                                                   flow_type=line[3], source=node_id,
                                                   destination=destination_id,
                                                   rate=int(line[9][1:]))
                    elif 'OFF' in line:
                        line = line.split()
                        self.flows[int(line[-1])].set_finish_time(finish_time=float(line[0]))
        self.clients = list(self.clients)

        for node_id in self.servers:
            with open('%s/node-%d/mgen.out' % (Constant.CP_CONFIG_DIRECTORY, node_id), 'r') as f:
                for line in f:
                    if 'RECV' not in line:
                        continue
                    line = line.split()
                    flow_id = int(line[3].split('>')[1])
                    seq_id = int(line[4].split('>')[1])
                    size = int(line[8].split('>')[1])
                    self.flows[flow_id].add_seq(seq_id=seq_id, size=size)

    def draw_figures(self):
        self.print_flows()

        plt.figure()
        for flow in self.flows.values():
            x = range(int(floor(flow.start_time)), int(ceil(flow.finish_time)))
            num_pkt_per_sec = flow.rate / 600 / 8
            y = []
            for i in range(len(x)):
                s = 0
                for j in range(num_pkt_per_sec):
                    index = i * num_pkt_per_sec + j
                    if index in flow.seqs:
                        s += flow.seqs[index]
                y.append(s * 8)
            plt.plot(x, y, label="Flow %d" % flow.flow_id)
        plt.legend()
        plt.show()

    def print_flows(self):
        for flow in self.flows.values():
            print(flow)


if __name__ == "__main__":
    print('Please run it using emane-docker interface: `emane-docker --draw-results` '
          'after running an experiment')
