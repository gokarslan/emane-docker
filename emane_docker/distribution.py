#!/usr/bin/env python3

import sys

import numpy as np

from emane_docker.log import LOG


def parse_distribution(dist_conf):
    try:
        if 'interval' in dist_conf:
            return dist_conf['interval']
        if 'min' in dist_conf:
            if 'max' not in dist_conf:
                return 'min and max interval must be specified together in the configuration'
            if 'increase_by' in dist_conf:
                return list(range(dist_conf['min'], dist_conf['max'], dist_conf['increase_by']))
        return 'min/max specified but increase factor is not specified in the configuration'
    except KeyError as kexc:
        return 'Unexpected key in configuration %s' % kexc
    except Exception as exc:
        return 'Exception %s' % exc


class DistributionParser:
    def __init__(self, distribution):
        self.simulation_id = -1
        # parse different distribution types
        if 'exponential' in distribution:
            self.get_next = self._get_next_exponential
            if 'beta' not in distribution['exponential']:
                LOG.error('Exponential distribution must have beta (1/lambda) value.')
                sys.exit(-1)
            self.betas = parse_distribution(distribution['exponential']['beta'])
            if not isinstance(self.betas, list):
                LOG.error(self.betas)
                sys.exit(-1)
            self.num_simulations = len(self.betas) if 'is_limited' not in distribution else float(
                'inf')
        elif 'single' in distribution:
            self.get_next = self._get_next_single
            self.elements = parse_distribution(distribution['single'])
            if not isinstance(self.elements, list):
                LOG.error(self.elements)
                sys.exit(-1)
            self.num_simulations = len(
                self.elements) if 'is_limited' not in distribution else float('inf')
        else:
            LOG.error('Unknown distribution type %s', distribution)
            sys.exit(-1)

    def start_next_simulation(self):
        if self.simulation_id < self.num_simulations - 1:
            self.simulation_id += 1
            return True
        return False

    def rewind(self):
        self.simulation_id = -1

    def _get_next_exponential(self):
        return np.random.exponential(self.betas[self.simulation_id], 1)[0]

    def _get_next_single(self):
        return np.random.choice(self.elements)
