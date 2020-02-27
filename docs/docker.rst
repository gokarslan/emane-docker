.. _docker:

.. |docker-version| replace:: 0.0.1


Building Docker Images
=======================

Current Containers
-------------------

EMANE-Docker platform comes with two Docker images listed in `docker/` folder.

1. `docker/emane`
    This is a intermediate Docker image containing `EMANE <https://github.com/adjacentlink/EMANE>`_, `OpenTestPoint <https://github.com/adjacentlink/opentestpoint>`_ and `OpenTestPoint-EMANE <https://github.com/adjacentlink/opentestpoint-probe-emane>`_. The production code should not use this container. This container is based on Ubuntu:16.04.

2. `docker/emane-docker`
    This is the main Docker image based on `docker/emane` and contains the routing protocols provided by `Quagga <https://github.com/Quagga/quagga>`_ , `OLSR <https://github.com/OLSR/olsrd>`_ and `OLSRv2 <https://github.com/OLSR/OON>`_.

Current docker image version is |docker-version|.

Building a Docker Image
------------------------------
To build an existing container locally, run

.. code-block:: console

    cd docker
    ./build.sh <Dockerfile-folder> <image-tag>:[version]

For example, to build `docker/emane-docker` locally, run

.. code-block:: console

    cd docker
    ./build.sh emane-docker emane-docker


If you want to create a new Docker image, you can simply create a folder under `docker/`, then create a Dockerfile
inside of that folder. After that, follow the building steps described above.

Changing Configurations to Use Local Docker Images
-------------------------------------------------
By default, EMANE-Docker uses the docker images under `Docker Hub <https://hub.docker.com/u/gokarslan>`_. You can change this by
changing the `docker_image` field in the EMANE-Docker configuration file. See :ref:`configuration` for more details.
