ifndef JAVA_HOME
    $(error JAVA_HOME not set)
endif

INCLUDE= -I"$(JAVA_HOME)/include" -I"$(JAVA_HOME)/include/linux"
CFLAGS=-Wall -Werror -fPIC -shared $(INCLUDE)

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

test: all java_test_targets
	tox -e test

test_jvm: all java_test_targets
	tox -e test_jvm

test_all: all java_test_targets test test_jvm

docker:
	docker build . -t jolynch/jvmquake:test
	docker run jolynch/jvmquake:test
