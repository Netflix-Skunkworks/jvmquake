ARG UBUNTU_VERSION=18.04
FROM ubuntu:$UBUNTU_VERSION

RUN apt-get update
RUN apt-get install -y debhelper

WORKDIR /work/packaging

COPY packaging /work/packaging
COPY build/libjvmquake-linux-x86_64.so /work/packaging/libjvmquake.so

CMD ["dpkg-buildpackage", "-us", "-uc"]
