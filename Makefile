ifndef JAVA_HOME
    $(error JAVA_HOME not set)
endif

INCLUDE= -I"$(JAVA_HOME)/include" -I"$(JAVA_HOME)/include/linux"
CFLAGS=-Wall -Werror -fPIC -shared $(INCLUDE) -lrt

TARGET=libjvmquake.so

.PHONY: all clean test

all:
	gcc $(CFLAGS) -o $(TARGET) jvmquake.c
	chmod 644 $(TARGET)

java_test_targets:
	${JAVA_HOME}/bin/javac tests/*.java

clean:
	rm -f $(TARGET)
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
	docker build -f dockerfiles/Dockerfile.bionic . -t jolynch/jvmquake:test_bionic
	docker build -f dockerfiles/Dockerfile.xenial . -t jolynch/jvmquake:test_xenial
	docker run jolynch/jvmquake:test_bionic && docker run jolynch/jvmquake:test_xenial
