#!/usr/bin/env python3

import matplotlib.pyplot as plt
import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout

from emane_docker.log import LOG


def draw(nodes, out_file=None):
    """
    Draws the given topology.

    :param nodes: List of nodes in the topology.
    :param out_file: If specified, the topology figure is saved to that file.
    :return:
    """
    graph = nx.Graph()
    for node in nodes.values():
        graph.add_node(node.name, time=node.id)
        for neighbor_name in node.neighbors:
            graph.add_edge(node.id, neighbor_name)

    # pos = nx.spring_layout(G, scale=20)
    # nx.spring_layout(G, k=0.05, iterations=20)
    options = {
        'node_size': 10,
        'font_size': 12,
        'with_labels': True,
        'pos': graphviz_layout(graph)
    }
    nx.draw(graph, **options)
    if out_file is None:
        plt.plot()
        plt.show()
    else:
        plt.savefig(out_file)
        LOG.info('The topology figure is saved to %s', out_file)


if __name__ == '__main__':
    print('Please run it using emane-docker interface: `emane-docker --draw-topology` '
          'or emane-docker --draw-topology --figure-path=<path>')
