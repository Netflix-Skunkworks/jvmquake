.PHONY: all clean test

BUILD ?= build

all:
	mkdir -p $(BUILD)
	BUILD=../build make -C src

java_test_targets:
	make -C tests

clean:
	rm -rf build
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

docker:
	mkdir -p $(BUILD)
	docker container rm -f jvmquake-build || true
	docker build -f dockerfiles/build/Dockerfile . -t jolynch/jvmquake:build
	docker container create --name jvmquake-build jolynch/jvmquake:build
	docker container cp jvmquake-build:/work/build/. ./build/
	docker container rm -f jvmquake-build

	#docker build -f dockerfiles/Dockerfile.xenial . -t jolynch/jvmquake:test_xenial
	#docker run jolynch/jvmquake:test_bionic && docker run jolynch/jvmquake:test_xenial

test_in_docker:
	tox -e test
	tox -e test_jvm
