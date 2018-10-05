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
	rm -f tests/*.class

easy: all
	$(JAVA_HOME)/bin/javac tests/EasyOOM.java
	$(JAVA_HOME)/bin/java -Xmx1m \
	    -XX:+HeapDumpOnOutOfMemoryError \
	    -XX:OnOutOfMemoryError='/bin/echo running OnOutOfMemoryError' \
	    -agentpath:$(PWD)/$(TARGET) \
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
