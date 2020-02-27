#!/usr/bin/env bash
apt-get -y update
apt-get -y install \
  apt-transport-https \
  ca-certificates \
  curl \
  gnupg-agent \
  graphviz \
  graphviz-dev \
  python-tk \
  python3-pip \
  software-properties-common \
  autoconf \
  automake \
  bridge-utils \
  build-essential \
  debhelper \
  dh-python \
  fping \
  gcc \
  g++ \
  git \
  gpsd \
  gpsd-clients \
  libpcap-dev \
  libpcre3-dev \
  libprotobuf-dev \
  libsqlite3-dev \
  libtool \
  libxml2-dev \
  libzmq3-dev \
  mgen \
  pkg-config \
  protobuf-compiler \
  python-dev \
  python-lxml \
  python-pmw \
  python-protobuf \
  python3-protobuf \
  python-setuptools \
  python3-setuptools \
  python-stdeb \
  python-tk \
  uuid-dev
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
add-apt-repository \
  "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"
apt-get -y update && apt-get -y install docker-ce docker-ce-cli containerd.io
pip3 install --upgrade pip
pip3 install -r /root/emane-docker/requirements.txt
cd /root && git clone https://github.com/adjacentlink/emane.git && cd emane && git checkout v1.2.4
./autogen.sh && ./configure && make deb WITHOUT_PYTHON3=1
cd .debbuild && dpkg -i *.deb && apt-get -y install -f && cd /root && rm -rf emane
