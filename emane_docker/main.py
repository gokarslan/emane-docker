#!/usr/bin/env python3

import argparse
import os
import sys

from colorama import init
from termcolor import cprint
from pyfiglet import figlet_format
import yaml

from emane_docker.log import LOG
from emane_docker.log import setup as log_setup
from emane_docker.log import add_file_logger
from emane_docker.result_report import Report
from emane_docker.topology import EmaneTopology
from emane_docker.topology_drawer import draw


def main():
    """
    The main function sets up the environment by reading the command line and configuration file
    and runs EMANE-Docker platform.

    :returns: 0 after a successful execution.
    """
    os.system('stty sane')

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--start', dest='start',
                        action='store_true',
                        default=False,
                        help='run EMANE-Docker')
    parser.add_argument('-S', '--stop', dest='stop',
                        action='store_true',
                        default=False,
                        help='stop EMANE-Docker')
    parser.add_argument('-y', action='store_true', dest='y', default=False,
                        help='answer yes to all prompts')
    parser.add_argument('-c', '--config-file', dest='config_file',
                        default='emane_docker/config.default.yaml',
                        help='path for configuration file')
    parser.add_argument('-t', '--topology-file', dest='topology_file',
                        default=None,
                        help='path to the topology file, overrides he path in configuration file')
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s {version}'.format(version='0.0.1'))
    parser.add_argument('--no-cli', action='store_true', dest='no_cli', default=False,
                        help='do not run EMANE-Docker CLI')
    parser.add_argument('--no-log', action='store_true', dest='no_log', default=False,
                        help='do not output logs')
    parser.add_argument('--debug', action='store_true', dest='debug', default=False,
                        help='set log level to debug')
    parser.add_argument('--draw-topology', action='store_true', dest='draw_topology', default=False,
                        help='draw current topology file')
    parser.add_argument('--figure-path', action='store', dest='figure_path', default=None,
                        help='output path for figure, if --draw-topology is specified')

    opts, _ = parser.parse_known_args()

    if opts.no_log:
        add_file_logger(os.devnull)
    else:
        log_setup(debug=opts.debug)
        try:
            init(strip=not sys.stdout.isatty())
            print('\n')
            cprint(figlet_format('EMANE-Dkr', font='speed'), 'blue')  # attrs=['bold']
        except Exception as exc:
            LOG.debug('Cannot use cprint, this might affect logging.')
            LOG.debug(exc.__traceback__)
            print('EMANE-Docker')

    # Read configuration
    config = None
    with open(opts.config_file, 'r') as f:
        config = yaml.load(f)
    if not config:
        LOG.error('Incorrect config file at %s', opts.config_file)
        return -1

    if opts.topology_file is not None:
        config['topology_file'] = opts.topology_file

    if 'no_cli' not in config:
        config['no_cli'] = opts.no_cli

    emane_topology = EmaneTopology(config=config)
    if opts.start:
        emane_topology.start()
    elif opts.stop:
        emane_topology.stop()
    elif opts.draw_topology:
        LOG.info('Saving the topology file at %s', opts.figure_path)
        draw(nodes=emane_topology.nodes, out_file=opts.figure_path)
    elif opts.draw_results:
        report = Report(num_nodes=4)
        report.draw_figures()

    return 0


if __name__ == '__main__':
    sys.exit(main())
