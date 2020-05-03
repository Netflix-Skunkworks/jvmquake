ifndef JAVA_HOME
    $(error JAVA_HOME not set)
endif

BUILD ?= ../build
INCLUDE= -I"$(JAVA_HOME)/include" -I"$(JAVA_HOME)/include/linux"
CFLAGS=-Wall -Werror -fPIC -shared $(INCLUDE) -lrt

TARGET=$(BUILD)/libjvmquake.so

.PHONY: all

all:
	mkdir -p $(BUILD)
	$(CC) -v
	$(CC) $(CFLAGS) -o $(TARGET) jvmquake.c
	chmod 644 $(TARGET)

