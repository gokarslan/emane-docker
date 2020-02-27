Installation
=============

EMANE-Docker platform requires Ubuntu 16.04 (or higher) or Centos 7 (or higher). There are different
ways to run EMANE-Docker. You can deploy using Vagrant and VirtualBox


Installation with Vagrant (recommended for beginning)
-----------------------------------------------------
You can run EMANE-Docker on a virtual machine (VM), if you want to test EMANE-Docker on a small topology
this method is recommended. Follow the steps below to run EMANE-Docker:

1.  Install `Vagrant <https://www.vagrantup.com/downloads.html>`_ and
    `VirtualBox <https://www.virtualbox.org/>`_ on your machine.
2.  Clone this repository by running ``git clone https://github.com/gokarslan/emane-docker``.
3.  Go to the `emane-docker` directory and run ``vagrant up``. This command will bootstrap a VM
    running Ubuntu 16.04. Wait until Vagrant starts the VM and installs necessary packages.
4.  SSH into the VM by running ``vagrant ssh``.
5.  EMANE-Docker requires `sudo` privileges. Run ``sudo su`` to switch to the `root` user.
6.  Go to `/root/emane-docker` directory by running ``cd ~/emane-docker``.
7.  You can now run EMANE-Docker by simply running ``./emane-docker --start``. This will deploy the
    topology under `emane_docker/topology.default.yaml`. Please refer to :ref:`configuration` for
    the details of configuring EMANE-Docker.
8.  You can destroy the VM by running ``vagrant destroy``. This will stop and remove the VM.



