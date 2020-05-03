ARG UBUNTU_VERSION=18.04
FROM ubuntu:$UBUNTU_VERSION

RUN apt-get update
RUN apt-get install -y debhelper

WORKDIR /work

COPY packaging/debian /work/debian
COPY build/libjvmquake-linux-x86_64.so /work/libjvmquake.so

CMD ["dpkg-buildpackage", "-us", "-uc"]
