.PHONY: all clean test

BUILD ?= build
DIST ?= dist

all:
	mkdir -p $(BUILD)
	BUILD=../build make -C src

java_test_targets:
	make -C tests

clean:
	rm -rf build
	rm -rf dist
	rm -f *.class
	rm -f *.hprof
	rm -f core
	rm -f gclog
	rm -f *.ran
	rm -f tests/*.class
	rm -rf tests/__pycache__
	rm -rf .tox

test_jvmquake: all java_test_targets
	tox -e test

test_jvm: all java_test_targets
	tox -e test_jvm

test: all java_test_targets test_jvmquake test_jvm

build_in_docker:
	mkdir -p $(BUILD)
	docker container rm -f jvmquake-build || true
	docker build -f dockerfiles/build/Dockerfile . -t jolynch/jvmquake:build
	docker container create --name jvmquake-build jolynch/jvmquake:build
	docker container cp jvmquake-build:/work/build/. ./$(BUILD)/
	docker container rm -f jvmquake-build

build_deb_in_docker: build_in_docker
	mkdir -p $(DIST)
	docker container rm -f jvmquake-debbuild || true
	docker build -f dockerfiles/packaging/Dockerfile . -t jolynch/jvmquake:debbuild
	docker run --name jvmquake-debbuild jolynch/jvmquake:debbuild
	docker cp jvmquake-debbuild:/work/. ./$(DIST)/
	docker rm -f jvmquake-debbuild

# Ubuntu builds test with both the 
test_xenial_java8: build_deb_in_docker
	docker build -f dockerfiles/test/Dockerfile.ubuntu --build-arg UBUNTU_VERSION=16.04 --build-arg JAVA_VERSION=8 . -t jolynch/jvmquake:$@
	docker run --rm -v $(shell pwd)/build/:/work/build/ jolynch/jvmquake:$@
	docker run --rm -v $(shell pwd)/dist/:/work/dist/ jolynch/jvmquake:$@

test_bionic_java8: build_deb_in_docker
	docker build -f dockerfiles/test/Dockerfile.ubuntu --build-arg UBUNTU_VERSION=18.04 --build-arg JAVA_VERSION=8 . -t jolynch/jvmquake:$@
	docker run --rm -v $(shell pwd)/build/:/work/build/ jolynch/jvmquake:$@
	docker run --rm -v $(shell pwd)/dist/:/work/dist/ jolynch/jvmquake:$@

test_focal_java8: build_deb_in_docker
	docker build -f dockerfiles/test/Dockerfile.ubuntu --build-arg UBUNTU_VERSION=20.04 --build-arg JAVA_VERSION=8 . -t jolynch/jvmquake:$@
	docker run --rm -v $(shell pwd)/build/:/work/build/ jolynch/jvmquake:$@
	docker run --rm -v $(shell pwd)/dist/:/work/dist/ jolynch/jvmquake:$@

test_centos7_java8: build_in_docker
	docker build -f dockerfiles/test/Dockerfile.centos --build-arg CENTOS_VERSION=7 --build-arg JAVA_VERSION=1.8.0 . -t jolynch/jvmquake:$@
	docker run --rm -v $(shell pwd)/build/:/work/build/ jolynch/jvmquake:$@
