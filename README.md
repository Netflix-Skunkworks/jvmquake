# jvmquake
A JVMTI agent that attaches to your JVM and kills it when things go sideways

This project is heavily inspired by `airlift/jvmkill` written by
`David Phillips <david@acz.org>` but adds the additional innovation of
a detection algorithm for when a JVM is unstable but not quite dead.

**NOT PRODUCTION READY**
I still have a number of todos to do before this is production ready, I'd
strongly recommend against using it at this stage

# Building
```bash
# Ensure that JAVA_HOME is pointing to the JVM you want to build for

make

# Now the agent is available at lib-jvm-watchdog.so
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
java -agentpath:/path/to/lib-jvmquake.so <your java program here>
```
