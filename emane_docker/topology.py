#!/usr/bin/env python3


from copy import deepcopy
from functools import total_ordering
import os
import shutil
import sys
from signal import signal, SIGINT
from time import sleep
import tarfile
from multiprocessing.pool import ThreadPool

from jinja2 import Environment, FileSystemLoader
from redis import Redis
import yaml

import docker

from emane_docker.constant import Constant
from emane_docker.event_generator import EventGenerator
from emane_docker.log import LOG
from emane_docker.util import mkdir_p
from emane_docker.traffic_generator import TrafficGenerator


class Node:
    """
    It contains information related to each "emulated" node. Each node runs as a separate
    Docker container. The names node and node are used interchangeably throughout this project.

    :param domain: The domain that node belongs to.
    :param node: The node dictionary, see the configuration examples for details.
    """

    def __init__(self, domain, node, index, as_id):
        """
        Initializes a node instance.

        """
        self.domain = domain
        self.name = node['name']
        # later support auto id assignment
        self.index = index
        self.as_id = as_id
        self.id = node['name']
        self.neighbors = node['neighbors']
        self.is_border = node['is_border']
        self.bootstrapfile = node[
            'bootstrapfile'] if 'bootstrapfile' in node else '/bootstrap/start.sh'
        self.port_offset = 0
        self.links = []

    def __str__(self):
        return 'Name: %s, Neighbors: %s' % (self.name, ', '.join(self.neighbors))

    def __eq__(self, other):
        return other.id == self.id


@total_ordering
class Link:
    """
    Contains the information related to a link between two nodes (nodes).

    :param node1:
    :param node2:
    :param mask1:
    :param mask2:
    :param lid:
    :param ip1:
    :param ip2:
    """
    LINK_COUNT = 0
    UP = 1
    DOWN = 0

    def __init__(self, node1, node2, mask1=24, mask2=24, lid=None, ip1=None, ip2=None):
        self.node1 = node1
        self.node2 = node2
        if lid is None:
            self.id = Link.LINK_COUNT
        else:
            self.id = lid
        Link.LINK_COUNT += 1
        self.node1_portid = None
        self.node2_portid = None
        if ip1 is None or ip2 is None:
            self._init_ipv4_addresses()
            self.mask1 = mask1
            self.mask2 = mask2
        else:
            if '/' in ip1:
                self.node1_ipv4, self.mask1 = ip1.split('/')[0], int(ip1.split('/')[1])
            else:
                self.node1_ipv4 = ip1
                self.mask1 = mask1
            if '/' in ip2:
                self.node2_ipv4, self.mask2 = ip2.split('/')[0], int(ip2.split('/')[1])
            else:
                self.node2_ipv4 = ip2
                self.mask2 = mask2

        self.node1.links.append(self)
        self.node2.links.append(self)
        self.status = Link.UP

    def swap_nodes(self):
        tmp = self.node1
        self.node1 = self.node2
        self.node2 = tmp
        tmp = self.node1_portid
        self.node1_portid = self.node2_portid
        self.node2_portid = tmp
        tmp = self.mask1
        self.mask1 = self.mask2
        self.mask2 = tmp
        tmp = self.node1_ipv4
        self.node1_ipv4 = self.node2_ipv4
        self.node2_ipv4 = tmp

    def _init_ipv4_addresses(self):
        try:
            node1 = int(self.node1.name)
            node2 = int(self.node2.name)
            # special mode where node names directly shows the ip addresses
            if 1 <= node1 <= 255 and 1 <= node2 <= 255:
                if node1 <= node2:
                    self.node1_ipv4 = '1.{}.{}.1'.format(node1, node2)
                    self.node2_ipv4 = '1.{}.{}.2'.format(node1, node2)
                else:
                    self.node1_ipv4 = '1.{}.{}.2'.format(node2, node1)
                    self.node2_ipv4 = '1.{}.{}.1'.format(node2, node1)

            else:
                raise Exception
        except Exception:
            if self.node1.name <= self.node2.name:
                self.node1_ipv4 = '1.{}.{}.1'.format(self.id // 255 + 1, self.id % 255 + 1)
                self.node2_ipv4 = '1.{}.{}.2'.format(self.id // 255 + 1, self.id % 255 + 1)
            else:
                self.node1_ipv4 = '1.{}.{}.2'.format(self.id // 255 + 1, self.id % 255 + 1)
                self.node2_ipv4 = '1.{}.{}.1'.format(self.id // 255 + 1, self.id % 255 + 1)

    def set_port_ids(self, node1_portid, node2_portid):
        self.node1_portid = node1_portid
        self.node2_portid = node2_portid

    def contains(self, node1, node2=None):
        return (node1.name == self.node1.name and node2.name == self.node2.name) or (
                node2.name == self.node1.name and node1.name == self.node2.name)

    def __eq__(self, other):
        return (self.node1.name, self.node2.name) == (other.node1.name, other.node2.name)

    def __ne__(self, other):
        return self != other

    def __lt__(self, other):
        return (self.node1.name, self.node2.name) < (other.node1.name, other.node2.name)


class EmaneTopology:
    def __init__(self, config):
        file_loader = FileSystemLoader('evaluation/templates')
        self.jinja_env = Environment(loader=file_loader)
        self.docker_client = docker.from_env()
        self.config = config
        self.nodes = {}
        self.links = []
        self.containers = {}
        self.redis_clients = []
        self.platform = self.config.get('platform', None)
        self.emane_interface = 'emanenode0'
        self.event_generator = None
        self.traffic_generator = None
        # self.pool = ThreadPool()

        # Docker related variables
        self.port_ids = None

        self.load_topology()

    def generate_configs(self):
        config_cps = []
        for control_plane in self.config['control_planes']:
            if control_plane not in Constant.SUPPORTED_CONTROL_PLANES:
                LOG.error('Control plane %s is not supported. Only %s CPs are supported.',
                          control_plane, ', '.join(Constant.SUPPORTED_CONTROL_PLANES))
                return -1
            # There is no config for SDN
            if control_plane != Constant.SDN_CP:
                config_cps.append(control_plane)

        if os.path.exists(Constant.CP_CONFIG_DIRECTORY):
            shutil.rmtree(Constant.CP_CONFIG_DIRECTORY)

        LOG.info('Generating configuration files for %s CPs', ', '.join(config_cps))
        for node in self.nodes.values():
            config_path = '%s/%s' % (Constant.CP_CONFIG_DIRECTORY, node.name)
            mkdir_p(config_path)
            self.generate_zebra_config(config_path=config_path, node=node)
            for control_plane in config_cps:
                self.generate_cp_config(config_path=config_path, node=node,
                                        control_plane=control_plane)
            # TODO enable defining NEMs in configuration!
            emane_configuration = deepcopy(self.config['emane_configuration'])
            emane_configuration['platform'] = {
                'ip_address': '10.100.0.%s' % (node.index + 1),
                'transport': 'transvirtual',
                'nem_id': (node.index + 1)
            }
            self.generate_emane_config(config_path=config_path, node=node,
                                       emane_configuration=emane_configuration)

        LOG.info('Configuring initial scenario file using the topology information')
        self.generate_emane_scenario_eel()
        return 0

    def generate_zebra_config(self, config_path, node):
        # Zebra (Quagga) Configuration
        with open('%s/zebra.conf' % config_path, 'a') as f:
            f.write('hostname Router\npassword zebra\nenable password zebra')
            for i in range(self.config.get('number_of_route_announcements', 0)):
                f.write('ip route 10.%d.%d.%d/32 eth0\n' % (node.index, int(i / 255), int(i % 255)))

    def generate_cp_config(self, config_path, node, control_plane):
        """
        Generates control plane configurations. User can override the default values by specifying
        it at EMANE-Docker configuration file. See the config.default.yaml for details.

        :param config_path: Configuration path
        :param node: The node
        :param control_plane: The CP plane (OLSR, OLSRv2, OSPF, BGP, IS-IS and RIP)
        """
        if control_plane == Constant.OLSR_CP:
            with open('%s/olsrd.conf' % Constant.TEMPLATE_DIRECTORY, 'r') as f:
                olsrd_conf_template = f.read()

            with open('{}/olsrd.conf' % config_path, 'a') as f:
                f.write(olsrd_conf_template)
                ifaces = '\nInterface '
                for i in range(len(node.neighbors)):
                    ifaces += '"i{}" '.format(i)
                f.write(ifaces + '{}\n')
        elif control_plane == Constant.OLSRv2_CP:
            with open('%s/olsrd2.conf' % config_path, 'a') as f:
                # TODO: Remove
                # '[global]\n\tfork 1\n\tplugin mpr\n\tplugin olsrv2\n\tplugin olsrv2info\n'
                # TODO: END
                # lans = ""
                org = '1.0.0.0/8'
                for interface_id, link in enumerate(node.links):
                    # org = link.node1_ipv4 if node == link.node1 else link.node2_ipv4
                    config = '[interface=i%d]\n' % interface_id
                    config = config + '\thello_interval 0.5\n\thello_validity 2.5\n\t'
                    config = config + 'ifaddr_filter default_accept\n\t'
                    # config = config + 'ifaddr_filter {}.0/24\n\t'.format(link.node1_ipv4[:-2])
                    # config = config + 'ifaddr_filter 1.0.0.0/8\n\t'
                    config = config + 'bindto default_reject\n'
                    config = config + '\tbindto %s.0/24\n\n' % link.node1_ipv4[:-2]
                    # lans = lans + 'lan {}.0/24'.format(link.node1_ipv4[:-2]) + '\n\t'
                    f.write(config)
                    # break
                # f.write('[interface=lo]\n')
                f.write('[olsrv2]\n\toriginator %s\n\tnhdp_routable true\n\t' % org)
                f.write('tc_interval 1.0\n\ttc_validity 10.0\n')
        elif control_plane == Constant.OSPF_CP:
            with open('%s/ospfd.conf' % Constant.TEMPLATE_DIRECTORY) as f:
                ospfd_conf_template = f.read()

            with open('%s/ospfd.conf' % config_path, 'a') as f:
                f.write(ospfd_conf_template)
                networks = ''
                for interface_id, link in enumerate(node.links):
                    interface_ip = link.node1_ipv4 if link.node1 == node else link.node2_ipv4
                    mask = link.mask1 if link.node1 == node else link.mask2
                    f.write('interface i%d\n' % interface_id)
                    f.write('\tip ospf dead-interval minimal hello-multiplier 10\n')
                    f.write('\tip ospf retransmit-interval 1\n')
                    # '\tip ospf hello-interval 1\n\tip ospf dead-interval 10\n\t
                    # ip ospf retransmit-interval 3\n')
                    # f.write('\tip ospf cost 50\n')
                    networks += '\tnetwork %s/%d area 0\n' % (interface_ip, mask)
                f.write('router ospf\n')
                f.write('\ttimers throttle lsa all 0\n\ttimers lsa arrival 0\n')
                f.write('\tredistribute static\n\tredistribute kernel\n')
                f.write(networks + '\n')
        elif control_plane == Constant.BGP_CP:
            with open('%s/bgpd.conf' % Constant.TEMPLATE_DIRECTORY) as f:
                bgpd_conf_template = f.read()

            with open('%s/bgpd.conf' % config_path, 'a') as f:
                f.write(bgpd_conf_template)
                f.write('router bgp %s\n' % node.as_id)
                f.write('\tneighbor provider_ip update-source %s\n' % node.as_id)
                f.write('\tredistribute static\n\tredistribute kernel\n')
                networks = ''
                neighbors = ''
                for interface_id, link in enumerate(node.links):
                    if link.node1 == node:
                        interface_ip = link.node1_ipv4
                        neighbor_ip = link.node2_ipv4
                        neighbor_as = link.node2.as_id
                        mask = link.mask1
                    else:
                        interface_ip = link.node2_ipv4
                        neighbor_ip = link.node1_ipv4
                        neighbor_as = link.node1.as_id
                        mask = link.mask2
                    # interface_ip = link.node1_ipv4 if link.node1 == node else link.node2_ipv4
                    networks += '\tnetwork %s/%d\n' % (interface_ip, mask)
                    neighbors += '\tneighbor %s remote-as %s\n' % (neighbor_ip, neighbor_as)
                    neighbors += '\tneighbor %s advertisement-interval 0\n' % neighbor_ip
                    neighbors += '\tneighbor %s peer-group upstream\n' % neighbor_ip
                f.write('%s\n%s' % (networks, neighbors))
        elif control_plane == Constant.ISIS_CP:
            with open('%s/isisd.conf' % Constant.TEMPLATE_DIRECTORY) as f:
                isisd_conf_template = f.read()

            with open('%s/isisd.conf' % config_path, 'a') as f:
                f.write(isisd_conf_template)
                networks = ''
                for interface_id, link in enumerate(node.links):
                    interface_ip = link.node1_ipv4 if link.node1 == node else link.node2_ipv4
                    mask = link.mask1 if link.node1 == node else link.mask2
                    f.write('Interface i%d\n' % interface_id)
                    f.write('\tip isis hello-interval 1\n')

                f.write('router isis IS\n')
                f.write('isis net 47.0001.1720.1700.0%03d.00' % (node.index + 2))

        elif control_plane == Constant.RIP_CP:
            with open('%s/ripd.conf' % Constant.TEMPLATE_DIRECTORY) as f:
                ripd_conf_template = f.read()

            with open('%s/ripd.conf' % config_path, 'a') as f:
                f.write(ripd_conf_template)
                networks = ''
                for interface_id, link in enumerate(node.links):
                    interface_ip = link.node1_ipv4 if link.node1 == node else link.node2_ipv4
                    mask = link.mask1 if link.node1 == node else link.mask2
                    # f.write('Interface i%d\n' % interface_id)
                    # f.write('\tip isis hello-interval 1\n')

                    networks += '\tnetwork %s/%d\n' % (interface_ip, mask)
                f.write('router rip\n')
                f.write(networks)

                # f.write('\ttimers throttle lsa all 0\n\ttimers lsa arrival 0\n')
                # f.write('\tredistribute static\n\tredistribute kernel\n' + networks)
                # f.write(networks + '\n')

        else:
            LOG.error('Unknown control plane type %s', control_plane)

    def load_topology(self):
        """
        Loads the topology file specified by the user (either in configuration file or as a command
        line parameter.

        """
        topology = None
        topology_file = self.config.get('topology_file', None)
        if not topology_file:
            LOG.error('Please specify a topology file')
            sys.exit(-1)
        try:
            with open(topology_file, 'r') as f:
                topology = yaml.load(f)
                all_nodes = []
                domains = dict()
                # Put all nodes in a single list
                for domain in topology['nodes']:
                    all_nodes.extend(topology['nodes'][domain])
                    domains.update({node['name']: domain for node in topology['nodes'][domain]})

                for index, node in enumerate(sorted(all_nodes, key=lambda x: x['name'])):
                    as_id = node['as_number'] if 'as_number' in node else 1000 + index
                    self.nodes[node['name']] = Node(domain=domains[node['name']], node=node,
                                                    index=index, as_id=as_id)
                for node in self.nodes.values():
                    for neighbor_name in node.neighbors:
                        exists = False
                        neighbor_node = self.nodes[neighbor_name]
                        for link in self.links:
                            if link.contains(node, neighbor_node):
                                exists = True
                        if not exists:
                            self.links.append(Link(node, neighbor_node))
                for i, link in enumerate(self.links):
                    if link.node1.index > link.node2.index:
                        self.links[i].swap_nodes()
                        # self.links[i] = Link(link.node2, link.node1)

                self.links = sorted(self.links)
                for i, link in enumerate(self.links):
                    link.id = i
                LOG.info('Topology (%s) with %d nodes and %d links is loaded.', topology_file,
                         len(self.nodes), len(self.links))

        except Exception as e:
            LOG.error('Incorrect topology file at %s', topology_file)
            LOG.debug('Exception: %s', e)
            sys.exit(-1)

    def start(self):
        """
        Starts EMANE-Docker

        :return:
        """
        signal(SIGINT, self.stop)
        # Generate configuration files for all CPs and all nodes
        self.generate_configs()
        if self.platform == Constant.PLATFORM_DOCKER:
            self.create_emane_interface()
            # Start containers using a thread pool
            self.run_threadpool(method=self.start_docker_container, params=self.nodes.values())

            # Wait for REDIS to start in each container
            sleep(Constant.REDIS_WAIT_TIME)

            if len(self.containers) == len(self.nodes):
                LOG.info('All nodes are started.')
            else:
                LOG.error('Some of the nodes cannot be started, removing all nodes...')
                return self.stop()

            # TODO: remove this, initial emane event service config should be enough
            # LOG.info('Configuring container links...')
            # # This needs to be sequential, can't use threadpool
            # self.port_ids = {node: 0 for node in self.nodes}
            # for link in self.links:
            #     self.configure_container_link(link)

            LOG.info('Starting helper programs in containers...')
            self.run_threadpool(method=self.start_container_helpers, params=self.nodes.values())

            LOG.info('Starting EMANE Event Service...')
            self.start_emane_eventservice()

            if self.config.get('no_cli', False):
                LOG.info('Skipping EMANE-Docker Controller CLI (--no-cli is set).')
                self.run_experiment(wait=True)

            else:
                LOG.info('Staring EMANE-Docker Controller CLI...')
                self.start_cli()
        else:
            LOG.error('Platform %s is not supported, supported platforms are %s', self.platform,
                      Constant.SUPPORTED_PLATFORMS)
            return -1

        return 0

    def stop(self, sig=None, frame=None):
        """
        Stops EMANE-Docker

        :param sig: Signal type (Expected: SIGINT)
        :param frame:
        :return:
        """
        LOG.info('Stopping all nodes...')

        if self.platform == Constant.PLATFORM_DOCKER:
            # Start containers using a thread pool
            threadpool = ThreadPool()
            threadpool.map(self.stop_docker_container, self.nodes.values())
            threadpool.close()
            threadpool.join()

            self.remove_emane_interface()

        else:
            LOG.error('Platform %s is not supported, supported platforms are %s', self.platform,
                      Constant.SUPPORTED_PLATFORMS)
            return -1

        LOG.info('All nodes are stopped.')

        # Stop is requested using Ctrl-C, exit from the program.
        if sig is not None:
            sys.exit(0)
        return 0

    def run_threadpool(self, method, params):
        """
        Runs a threadpool for given methods and params. Used when starting/stopping/configuring
        nodes. It blocks until the threadpool finishes.

        :param method: The method to run
        :param params: Method parameters
        """
        threadpool = ThreadPool()
        threadpool.map(method, params)
        threadpool.close()
        threadpool.join()

    def start_cli(self):
        """
        Starts EMANE-Docker CLI.

        """
        # Initialize connection method to nodes depending on the platform
        if self.platform == Constant.PLATFORM_DOCKER:
            for container in self.containers:
                ip = str(self.docker_client.containers.get(container).attrs['NetworkSettings'][
                             'Networks']['bridge']['IPAddress'])
                self.redis_clients.append(Redis(host=ip, port=6379, db=0))

        else:
            LOG.error('Platform %s is not supported, supported platforms are %s', self.platform,
                      Constant.SUPPORTED_PLATFORMS)
            return -1
        while True:
            command = input('emane-docker> ')
            # TODO: update commands START
            if command == 'quit':
                break
            if command == 'start-experiment':
                LOG.info('Experiment will be initialized now... '
                         'CLI will not be accessible meanwhile.')
                self.run_experiment(wait=False)
            elif command == 'start-event-generator':
                self.start_event_generator()
            elif command == 'start-traffic-generator':
                self.start_traffic_generator()
            # if command == 'init':
            #     for r in self.redis_clients:
            #         r.publish('cmd', 'init')
            elif command == ('help', '?'):
                print('Available commands are:\n%s' % '\n'.join(['help', 'quit']))
            # TODO: update commands! END
            else:
                print('%s is not a valid command. Type `help` to see available commands.' % command)

        return self.stop()

    def start_docker_container(self, node):
        LOG.info('Starting node: %s', node.name)
        # This the port running Telegraf
        port = 20000 + node.index
        try:
            binding_path = os.getcwd() + '/container_helpers'
            config_path = '/configs/' + node.name
            container = self.docker_client.containers.run(self.config['docker_image'], detach=True,
                                                          network=self.emane_interface,
                                                          mac_address='02:00:%02x:01:00:01' % (
                                                                  node.index + 1),
                                                          cap_add=['sys_nice', 'NET_ADMIN'],
                                                          name=node.name,
                                                          privileged=True,
                                                          tty=True,
                                                          hostname=node.name,
                                                          ports={'{}/tcp'.format(port): port},
                                                          volumes={
                                                              config_path: {
                                                                  'bind': '/etc/quagga'},
                                                              binding_path + '/bootstrap': {
                                                                  'bind': '/bootstrap'},
                                                              binding_path + '/fpm': {
                                                                  'bind': '/fpm'},
                                                              '/lib/modules': {
                                                                  'bind': '/lib/modules',
                                                                  'mode': 'ro'},
                                                              '/dev/net/tun': {
                                                                  'bind': '/dev/net/tun'},
                                                              '/var/run/docker.sock': {
                                                                  'bind': '/var/run/docker.sock'}},
                                                          command=node.bootstrapfile)

            self.containers[node.name] = container
            # Create telegraf configuration and copy to the container.
            port = 20000 + node.index
            telegraf_conf_path = os.getcwd() + '/templates/telegraf.conf'
            with open(telegraf_conf_path, 'r') as src, open(
                    telegraf_conf_path + str(node.index), 'w') as dst:
                for line in src:
                    # Replace port number
                    if '20000' in line:
                        dst.write(line.replace('20000', str(port)))
                    else:
                        dst.write(line)
            self.container_cp(node, telegraf_conf_path + str(node.index),
                              '/etc/telegraf/telegraf.conf')
            os.remove(telegraf_conf_path + str(node.index))
            # Start telegraf
            container.exec_run('telegraf &', detach=True)

        except FileNotFoundError:
            return LOG.error('%s container cannot be started, is Docker daemon running?',
                             node.name)
        except Exception as exc:
            LOG.exception(exc)
            LOG.error('%s container cannot be started.', node.name)
            return -1
        LOG.info('Node %s is started.', node.name)
        return 0

    def stop_docker_container(self, node):
        try:
            self.docker_client.containers.get(node.name).remove(force=True)
        except Exception as exc:
            LOG.exception(exc)
            LOG.error('%s container cannot be stopped.', node.name)
        LOG.debug('The %s container is removed.', node.name)
        return 0

    def start_container_helpers(self, node):
        self.start_emane_on_node(node)
        LOG.debug('Configuring default rules for %s', node.name)
        # self.containers[node.name].exec_run('/bootstrap/default.py', detach=True)
        if Constant.OLSR_CP in self.config['control_planes']:
            LOG.debug('Starting OLSR at node %s', node.name)
            # self.containers[node.name].exec_run('/bootstrap/olsr.py', detach=True)
            self.containers[node.name].exec_run('olsrd -f /etc/quagga/olsrd.conf', detach=True)
        elif Constant.OLSRv2_CP in self.config['control_planes']:
            LOG.debug('Starting OLSRv2 at node %s', node.name)
            # self.containers[node.name].exec_run('/bootstrap/olsr2.py', detach=True)
            self.containers[node.name].exec_run('olsrd2_static -l /etc/quagga/olsrd2.conf',
                                                detach=True)
        else:
            # TODO: fix FPM
            if Constant.OSPF_CP in self.config['control_planes']:
                self.containers[node.name].exec_run('ospfd -d -f /etc/quagga/ospfd.conf',
                                                    detach=True)
            elif Constant.BGP_CP in self.config['control_planes']:
                self.containers[node.name].exec_run('bgpd -d -f /etc/quagga/bgpd.conf', detach=True)
            LOG.debug('Starting FPM in %s', node.name)
            # self.containers[node.name].exec_run('sudo python3 /fpm/main.py &', detach=True)
            self.containers[node.name].exec_run('python /fpm/main.py &', detach=True)
            LOG.debug('Starting FPM in %s', node.name)
            self.containers[node.name].exec_run('python3 /fpm/main.py &', detach=True)

    def container_cp(self, r, src, dst):
        container = self.docker_client.containers.get(r.id)
        tar = tarfile.open(src + '.tar', mode='w')
        try:
            tar.add(src, arcname='telegraf.conf')
        finally:
            tar.close()
        data = open(src + '.tar', 'rb').read()
        container.put_archive(os.path.dirname(dst), data)
        os.remove(src + '.tar')

    def jinja_renderer(self, temp_path, dest_path, confs):
        with open(temp_path, 'a') as f:
            f.write(self.jinja_env.get_template(dest_path).render(**confs))

    # EMANE RELATED FUNCTIONS
    def generate_emane_config(self, config_path, node, emane_configuration):
        with open('%s/platform.xml' % config_path, 'a') as f:
            platform = self.jinja_env.get_template('platform.xml')
            # ip_address=, transport
            platform = platform.render(**emane_configuration['platform'])
            # % 10.100.0.1 ieee80211abgnem
            f.write(platform)

        nem = emane_configuration['nem']
        with open('%s/nem.xml' % config_path, 'a') as f:
            f.write(self.jinja_env.get_template('nem.xml').render(**nem))

        # Create transport layer configuration
        if nem['transport'] == 'transvirtual':
            self.jinja_renderer('%s/transvirtual.xml' % config_path, 'transvirtual.xml', dict())
        else:
            LOG.error('Unknown transport layer %s', nem['transport'])

        # Create MAC layer configuration
        if nem['mac'] == 'ieee80211abg':
            self.jinja_renderer('%s/ieee80211abg.xml' % config_path, 'ieee80211abg.xml',
                                emane_configuration['ieee80211abg'])
        elif nem['mac'] == 'rfpipe':
            self.jinja_renderer('%s/rfpipe.xml' % config_path, 'rfpipe.xml',
                                emane_configuration['rfpipe'])
        else:
            LOG.error('Unknown MAC layer %s', nem['mac'])

        # Create PHY layer configuration
        if nem['phy'] == 'precomputed':
            self.jinja_renderer('%s/precomputed.xml' % config_path, 'precomputed.xml',
                                emane_configuration['precomputed'])
        else:
            LOG.error('Unknown PHY layer %s', nem['phy'])

    def generate_emane_scenario_eel(self):
        with open('evaluation/templates/scenario.eel', 'w') as f:
            # 0.0  nem:1 pathloss nem:2,50 nem:3,44 nem:4,45
            for node in self.nodes.values():
                node_nem = node.name.replace('node-', 'nem:')
                pathloss_list = []
                for neighbor_name in self.nodes:
                    if neighbor_name == node.name:
                        continue
                    neighbor_nem = neighbor_name.replace('node-', 'nem:')
                    if neighbor_name in node.neighbors:
                        pathloss_list.append('%s,0' % neighbor_nem)
                    else:
                        pathloss_list.append('%s,200' % neighbor_nem)
                f.write('0.0 %s pathloss %s\n' % (node_nem, ' '.join(pathloss_list)))

    def start_emane_on_node(self, node):
        LOG.debug('Starting EMANE at node %s', node.name)
        self.containers[node.name].exec_run('emane /etc/quagga/platform.xml -r -d -l 3 -f '
                                            '/var/log/emane.log --pidfile /var/run/emane.pid '
                                            '--uuidfile /var/run/emane.uuid')

    def start_emane_eventservice(self):
        os.system('emaneeventservice -d evaluation/templates/eventservice.xml -l 3 -f '
                  '/var/log/emaneeventservice.log --pidfile /var/run/emaneeventservice.pid '
                  '--uuidfile /var/run/emaneeventservice.uuid')
        LOG.debug('EMANE Event Service is started.')

    def create_emane_interface(self):
        LOG.debug('Creating docker interface (%s) for EMANE', self.emane_interface)
        os.system('docker network create --driver=bridge --subnet=10.99.0.100/24 '
                  '--opt com.docker.network.bridge.name=%s %s' % (
                      self.emane_interface, self.emane_interface))

    def remove_emane_interface(self):
        LOG.debug('Creating docker interface (%s) for EMANE', self.emane_interface)
        os.system('docker network rm %s' % self.emane_interface)

    def start_event_generator(self):
        self.event_generator = EventGenerator(nodes=self.nodes,
                                              link_update=self.config['experiment']['link_update'],
                                              duration=self.config['experiment']['duration'])
        self.event_generator.start()

    def start_traffic_generator(self):
        # Start MGEN traffic generator
        experiment = self.config['experiment']
        self.traffic_generator = TrafficGenerator(nodes=self.nodes,
                                                  containers=self.containers,
                                                  traffic_config=experiment['traffic'],
                                                  duration=experiment['duration'],
                                                  generate_configurations=False)
        # opts.generate_configurations)
        self.traffic_generator.start()

    def run_experiment(self, wait=False):
        if 'experiment' in self.config and self.config['experiment'].get('enabled', False):
            if wait:
                sleep_time = 1.0 * len(self.nodes)
                LOG.info('Waiting for %d seconds before running the experiment')
                sleep(sleep_time)
            LOG.info('Experiment is started.')
            self.start_traffic_generator()
            self.start_event_generator()
        else:
            LOG.debug('No experiments will be run, check the configuration file. '
                      'Either experiment is not configured or disabled.')
