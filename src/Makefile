ifndef JAVA_HOME
    $(error JAVA_HOME not set)
endif

BUILD ?= ../build
SO_NAME ?= libjvmquake-$(shell uname -s -m | tr 'A-Z' 'a-z' | tr ' ' '-').so
TARGET = $(BUILD)/$(SO_NAME)

INCLUDE = -I"$(JAVA_HOME)/include" -I"$(JAVA_HOME)/include/linux"
CFLAGS =-Wall -Werror -fPIC -shared $(INCLUDE) -lrt

.PHONY: all

all:
	mkdir -p $(BUILD)
	$(CC) -v
	$(CC) $(CFLAGS) -o $(TARGET) jvmquake.c
	chmod 644 $(TARGET)

