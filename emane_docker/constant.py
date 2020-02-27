#!/usr/bin/env python3


class Constant:
    def __init__(self):
        pass

    # Control Plane identifiers
    SDN_CP = "sdn"
    OSPF_CP = "ospf"
    OLSR_CP = "olsr"
    OLSRv2_CP = "olsrv2"
    BGP_CP = "bgp"
    ISIS_CP = "isis"
    RIP_CP = "rip"
    SUPPORTED_CONTROL_PLANES = [SDN_CP, OSPF_CP, OLSR_CP, OLSRv2_CP, BGP_CP, ISIS_CP, RIP_CP]

    # Platforms

    PLATFORM_DOCKER = "docker"
    SUPPORTED_PLATFORMS = [PLATFORM_DOCKER]

    # Paths
    CP_CONFIG_DIRECTORY = "container_helpers/configs"
    TEMPLATE_DIRECTORY = "templates"

    # Misc.

    REDIS_WAIT_TIME = 5.0
