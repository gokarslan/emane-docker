FROM ubuntu:16.04

ENV EMANE_VERSION "v1.2.4"
ENV OPENTESTPOINT_VERSION "v1.0.8"
ENV OPENTESTPOINT_EMANE_VERSION "v1.0.6"

# Run at ~
WORKDIR /root

# Install required packages
RUN apt-get -y update && apt-get -y install \
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
    libzmq-dev \
    mgen \
    pkg-config \
    protobuf-compiler \
    python-dev \
    python-lxml \
    python-pmw \
    python-protobuf \
    python-setuptools \
    python-stdeb \
    python-tk \
    uuid-dev

# Build EMANE
RUN git clone https://github.com/adjacentlink/emane.git \
    && cd emane \
    && git checkout $EMANE_VERSION \
    && ./autogen.sh \
    && ./configure \
    && make deb WITHOUT_PYTHON3=1
# Install EMANE
RUN cd emane/.debbuild \
    && dpkg -i *.deb \
    && apt-get -y install -f \
    && cd /root \
    && rm -rf emane

# Install additional dependencies required by OpenTestPoint
RUN apt-get -y update \
    && apt-get -y install \
    libzmq3-dev \
    python-zmq

# Build OpenTestPoint
RUN git clone https://github.com/adjacentlink/opentestpoint.git \
    && cd opentestpoint \
    && git checkout $OPENTESTPOINT_VERSION \
    && ./autogen.sh \
    && ./configure \
    && make deb
# Install OpenTestPoint
RUN cd opentestpoint/.debbuild \
    && dpkg -i *.deb \
    && apt-get -y install -f \
    && cd /root \
    && rm -r opentestpoint

# Build OpenTestPoint-EMANE
RUN git clone https://github.com/adjacentlink/opentestpoint-probe-emane.git \
    && cd opentestpoint-probe-emane \
    && git checkout $OPENTESTPOINT_EMANE_VERSION \
    && ./autogen.sh \
    && ./configure \
    && make deb
# Install OpenTestPoint-EMANE
RUN cd opentestpoint-probe-emane/.debbuild \
    && dpkg -i *.deb \
    && apt-get -y install -f \
    && cd /root \
    && rm -r opentestpoint-probe-emane

# Clean dangling packages
RUN apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
