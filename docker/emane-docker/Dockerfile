FROM gokarslan/emane:0.0.1

ENV QUAGGA_VERSION "1.2.4"
# This iPerf version supports smaller reporting intervals
ENV IPERF_VERSION "2.0.7"
ENV IPERF_BIN_NAME "iperf27"

ENV OLSR_VERSION "0.9.6"
ENV OLSRv2_VERSION "v0.15.1"

ENV TELEGRAF_VERSION "1.10.2-1"

# Install required packages
RUN apt-get -y update && apt-get install -y \
    bison \
    cmake \
    curl \
    debhelper \
    dnsutils \
    dpkg-dev \
    flex \
    gawk \
    gcc \
    git \
    iperf \
    iputils-ping \
    libc-ares-dev \
    libgps-dev \
    libgtk2.0-dev \
    liblua50-dev \
    libreadline-dev \
    net-tools \
    openvswitch-switch \
    pkg-config \
    protobuf-c-compiler \
    python3 \
    python3-pip \
    python3-tk \
    python-gtk2-dev \
    redis-server \
    tcpdump \
    telnet \
    texinfo \
    traceroute \
    vim \
    wget

# Install tshark for traffic monitoring
RUN apt-get -y update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y install tshark

# Install required Python3 packages
RUN pip3 install protobuf pyroute2 netifaces python_arptable ryu grequests redis

# Install Quagga for OSPF and BGP
RUN curl -O http://download-mirror.savannah.gnu.org/releases/quagga/quagga-$QUAGGA_VERSION.tar.gz \
    && tar zxvf ./quagga-$QUAGGA_VERSION.tar.gz \
    && cd quagga-$QUAGGA_VERSION \
    && ./configure --enable-fpm --enable-protobuf --enable-user=root \
        --enable-group=root --enable-vty-group=root \
    && make \
    && make install \
    && cp /usr/local/lib/lib* /lib/ \
    && mkdir /etc/quagga \
    && cp /usr/local/etc/zebra.conf.sample /etc/quagga/zebra.conf \
    && chmod 640 /etc/quagga/* \
    && cd .. \
    && rm -r quagga-$QUAGGA_VERSION.tar.gz quagga-$QUAGGA_VERSION

# Install OLSR
RUN git clone https://github.com/OLSR/olsrd \
    && cd olsrd \
	&& git checkout origin/release-$OLSR_VERSION \
	&& git remote add debbuild https://salsa.debian.org/debian/olsrd.git \
	&& git fetch debbuild \
	&& git checkout debbuild/master debian \
	&& echo "1.0" > debian/source/format \
	&& dpkg-buildpackage -uc -us \
	&& cd .. \
	&& yes | dpkg  -i olsrd_$OLSR_VERSION.1-1_amd64.deb \
	&& yes | dpkg  -i olsrd-plugins_$OLSR_VERSION.1-1_amd64.deb \
    && rm -r olsrd*

# Install OLSRv2
RUN git clone https://github.com/OLSR/OONF \
    && cd OONF/build \
    && git checkout tags/$OLSRv2_VERSION \
    && cmake .. \
    && make \
    && mv olsrd2_static /usr/bin \
    && cd ../.. \
    && rm -r OONF

# Install Telegraf for monitoring
RUN wget https://dl.influxdata.com/telegraf/releases/telegraf_$TELEGRAF_VERSION\_amd64.deb \
    && dpkg -i telegraf_$TELEGRAF_VERSION\_amd64.deb \
    && rm -rf telegraf_$TELEGRAF_VERSION\_amd64.deb

# Install iPerf2.7
RUN wget https://master.dl.sourceforge.net/project/iperf2/iperf-$IPERF_VERSION.tar.gz \
    && tar zxvf iperf-$IPERF_VERSION.tar.gz \
    && cd iperf-$IPERF_VERSION \
    && ./configure \
    && make \
    && cp src/iperf /usr/bin/$IPERF_BIN_NAME \
    && cd .. \
    && rm -r iperf-$IPERF_VERSION.tar.gz iperf-$IPERF_VERSION

# Clean dangling packets
RUN apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

