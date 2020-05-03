FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -y build-essential
RUN apt-get install -y openjdk-8-jdk-headless

WORKDIR /work

COPY src/ /work

RUN uname -s -m | tr A-Z a-z | tr ' ' - > /work/arch

ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
RUN BUILD=build SO_NAME=libjvmquake-$(cat /work/arch).so make
