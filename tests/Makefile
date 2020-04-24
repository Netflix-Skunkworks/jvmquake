
%.class: %.java
	javac $<

all: $(patsubst %.java,%.class, $(wildcard *.java))
