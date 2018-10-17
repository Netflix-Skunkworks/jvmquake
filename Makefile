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

test: all
	${JAVA_HOME}/bin/javac tests/*.java
	tox

docker:
	docker build . -t jolynch/jvmquake:test
	docker run jolynch/jvmquake:test

easy_thread: all
	$(JAVA_HOME)/bin/javac tests/EasyThreadOOM.java
	$(JAVA_HOME)/bin/java -Xmx1m \
	    -XX:+HeapDumpOnOutOfMemoryError \
		-Xmx100m \
	    -XX:OnOutOfMemoryError='/bin/echo running OnOutOfMemoryError' \
	    -agentpath:$(PWD)/$(TARGET) \
	    -cp $(PWD)/tests EasyThreadOOM

easy_opt: all
	$(JAVA_HOME)/bin/javac tests/EasyOOM.java
	$(JAVA_HOME)/bin/java -Xmx1m \
	    -XX:+HeapDumpOnOutOfMemoryError \
	    -XX:OnOutOfMemoryError='/bin/echo running OnOutOfMemoryError' \
	    -agentpath:$(PWD)/$(TARGET)=10,1,6 \
	    -cp $(PWD)/tests EasyOOM

easy_opt_oom: all
	$(JAVA_HOME)/bin/javac tests/EasyOOM.java
	$(JAVA_HOME)/bin/java -Xmx1m \
	    -XX:+HeapDumpOnOutOfMemoryError \
	    -XX:OnOutOfMemoryError='/bin/echo running OnOutOfMemoryError' \
	    -agentpath:$(PWD)/$(TARGET)=10,1,0 \
	    -cp $(PWD)/tests EasyOOM

hard: all
	$(JAVA_HOME)/bin/javac tests/SlowDeathOOM.java
	$(JAVA_HOME)/bin/java -Xmx100m \
	    -XX:OnOutOfMemoryError='/bin/echo OOMKILL' \
		-XX:+UseParNewGC \
		-XX:+UseConcMarkSweepGC \
		-XX:CMSInitiatingOccupancyFraction=75 \
		-XX:+PrintGCDetails \
		-XX:+PrintGCDateStamps \
		-XX:+PrintGCApplicationConcurrentTime \
		-XX:+PrintGCApplicationStoppedTime \
		-XX:+HeapDumpOnOutOfMemoryError \
		-Xloggc:gclog \
	    -agentpath:$(PWD)/$(TARGET) \
	    -cp $(PWD)/tests SlowDeathOOM

hard_opt: all
	$(JAVA_HOME)/bin/javac tests/SlowDeathOOM.java
	$(JAVA_HOME)/bin/java -Xmx100m \
	    -XX:OnOutOfMemoryError='/bin/echo OOMKILL' \
		-XX:+UseParNewGC \
		-XX:+UseConcMarkSweepGC \
		-XX:CMSInitiatingOccupancyFraction=75 \
		-XX:+PrintGCDetails \
		-XX:+PrintGCDateStamps \
		-XX:+PrintGCApplicationConcurrentTime \
		-XX:+PrintGCApplicationStoppedTime \
		-XX:+HeapDumpOnOutOfMemoryError \
		-Xloggc:gclog \
	    -agentpath:$(PWD)/$(TARGET)=1,1,6 \
	    -cp $(PWD)/tests SlowDeathOOM
