FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -y build-essential
RUN apt-get install -y openjdk-8-jdk-headless

WORKDIR /work

COPY src/ /work

ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
RUN BUILD=build make
