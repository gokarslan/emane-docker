.. _index:

EMANE-Docker Platform Documentation
========================================

EMANE-Docker is a platform to deploy and emulate distributed wireless networks using
`EMANE (Extendable Module Ad-hoc Network Emulator) <https://github.com/adjacentlink/emane>`_.
EMANE-Docker allows you to deploy arbitrary topologies with different routing protocols including OLSR,
OLSRv2 and OSPF, test different traffic loads (with MGEN and iPerf3) and network events with EMANE Event Generator.


.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   introduction
   installation
   configuration
   simple

.. toctree::
   :maxdepth: 2
   :caption: Routing

   olsr
   quagga

.. toctree::
   :maxdepth: 2
   :caption: Traffic Generation

   mgen
   iperf

.. toctree::
   :maxdepth: 2
   :caption: Event Generation

.. toctree::
   :maxdepth: 1
   :caption: Demos

   demos

.. toctree::
   :maxdepth: 1
   :caption: Advanced Usage

   docker
   plot


.. toctree::
   :maxdepth: 1
   :caption: About

   development
   copyright

.. toctree::
   :maxdepth: 1
   :caption: Source Documentation

   source/modules




..
   Indices and tables
   ==================

   * :ref:`genindex`
   * :ref:`modindex`
   * :ref:`search`
