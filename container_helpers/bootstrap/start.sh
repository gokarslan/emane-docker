#!/usr/bin/env bash
#service openvswitch-switch start
#ovs-vsctl add-br s
#ovs-vsctl set-controller s tcp:127.0.0.1:6633
#ovs-vsctl set-fail-mode s secure
zebra -d -f /etc/quagga/zebra.conf --fpm_format protobuf
#sleep 1
#redis-server > /dev/null 2>&1 &
#sleep 3
export PYTHONPATH="${PYTHONPATH}:/"
#ryu-manager /multijet/ryu_agent.py &
bash
