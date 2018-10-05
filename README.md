# jvmquake
A JVMTI agent that attaches to your JVM and kills it when things go sideways

The name comes from "jvm earth`quake`" (a play itself on hotspot).

This project is heavily inspired by [`airlift/jvmkill`](https://github.com/airlift/jvmkill)
written by `David Phillips <david@acz.org>` but adds the additional innovation of
a GC instability detection algorithm for when a JVM is unstable but not quite
dead yet.

**NOT PRODUCTION READY**
I still have a number of todos to do before this is production ready, I'd
strongly recommend against using it at this stage

Todos:

* Thorough testing (in progress)
* Configuration options on the algorithm (in progress)
* Documentation (in progress)
* Error handling (next)

# Building
```bash
# Ensure that JAVA_HOME is pointing to the JVM you want to build for and run

make

# Or you can run make with the JAVA_HOME specified manually

make JAVA_HOME=/path/to/jvm

# Now the agent is available at libjvmquake.so
```

# Testing
```bash
# Test out an easy OOM condition
make easy

# Test out a complicated OOM condition
make hard
```

# Using
Once you've got the agent built, to use it just run your java program
with `agent-path`

```
java -agentpath:/path/to/libjvmquake.so <your java program here>
```
