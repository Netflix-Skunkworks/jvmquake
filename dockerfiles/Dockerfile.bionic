FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -y openjdk-8-jdk build-essential
RUN apt-get install -y python3.6-minimal python3-pip

RUN python3.6 -m pip install pip --upgrade
RUN python3.6 -m pip install tox

ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64

COPY . /app
WORKDIR /app

RUN make
CMD ["make", "test"]
