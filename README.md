[![Build Status](https://travis-ci.org/jolynch/jvmquake.svg?branch=master)](https://travis-ci.org/jolynch/jvmquake)

# `jvmquake`
A JVMTI agent that attaches to your JVM and automatically signals and kills it
when the program has become unstable.

The name comes from "jvm earth`quake`" (a play itself on hotspot).

This project is heavily inspired by [`airlift/jvmkill`](https://github.com/airlift/jvmkill)
written by `David Phillips <david@acz.org>` but adds the additional innovation of
a GC instability detection algorithm for when a JVM is unstable but not quite
dead yet (aka "GC spirals of death").

**Beta Quality**
At this point I have written a thorough test suite, added error handling
everywhere, and have demonstrated this tool superior to the built in JVM
options. I am now testing this software in our production applications.

If you're not interested in why this is a good idea, head straight to
[Building and Usage](#building-and-usage) for how to build and use this agent.

# Motivation
Java Applications, especially databases such as Elasticsearch and Cassandra
can easily enter GC spirals of death, either resulting in eventual OOM or
Concurrent Mode Failures (aka "CMF" per CMS parlance although G1 has similar
issues with frequent mixed mode collections). Concurrent mode failures, when
the old gen collector is running frequently expending a lot of CPU resources
but is still able to reclaim enough memory so that the application does not
cause a full OOM, are particularly pernicious as they appear as 10-30s
"partitions" (duration is proportional to heap size) which repeatedly form
and heal ...

This grey failure mode *wreaks havoc* on distributed systems. In the case of
databases it can lead to degraded performance or even data corruption.  General
jvm applications that use distributed locks to enter a critical section may
make incorrect decisions under the assumption they have a lock when they in
fact do not (e.g. if the application pauses for 40s and then continues
executing assuming it still held a lock in Zookeeper).

As pathological heap situations are so problematic, the JVM has various flags
to try to address these issues:

* `OnOutOfMemoryError`: Commonly used with `kill -9 %p`. This options sometimes
works but most often results in no action, especially when the JVM is out of
file descriptors and can't execute the command at all. As of Java 8u92 there
is a better option in the `ExitOnOutOfMemoryError` option below. This option
furthermore does not handle excessive GC.
* `ExitOnOutOfMemoryError` and `CrashOnOutOfMemoryError`: Both options were
added as part of [JDK-8138745](https://bugs.openjdk.java.net/browse/JDK-8138745)
Both work great for dealing with running out memory, but do not handle other
edge cases such as [running out of threads](https://bugs.openjdk.java.net/browse/JDK-8155004).
Also naturally these do nothing when you are in the "grey" failure mode of CMF.

There are also some options that are supposed to control GC overhead:

* `GCHeapFreeLimit`, `GCTimeLimit` and `+UseGCOverheadLimit`. These options
are supposed to cause an OOM in the case where we are not collecting enough
memory, or are spending too much time in GC. However in practice I've never
been able to get these to work well, and `GCOverheadLimit` is afaik only
supported in CMS.

**TLDR**: In my experience these JVM flags are **hard to tune** and **only
sometimes work** if they work at all, and often are limited to a subset of JVMs
of collectors.

## Premise of `jvmquake`
`jvmquake` is designed with the following guiding principles in mind:

1. If my JVM becomes totally unusable (OOM, out of threads, etc), I want it to
   die.
2. If my JVM spends excessive time garbage collecting, I want it to die.
3. I may want to be able to debug why my JVM ran out of memory (e.g.
   heap dumps or core dumps).
4. This should work on any JVM (Java 6, Java 8, w.e.).

These principles are in alignment with **Crash Only Software**
([background](https://www.usenix.org/legacy/events/hotos03/tech/full_papers/candea/candea.pdf))
which implores us to crash when we encounter bugs instead of limping along.

## Knobs and Options
`jvmquake` has three options passed as three comma delimited integers
`<threshold,runtime_weight,action>`:

 * `threshold` (default: 30): the maximum GC "deficit" which can be
   accumulated before jvmquake takes action, specified in seconds.
 * `runtime_weight` (default: 5): the factor by which to multiply
   running JVM time, when weighing it against GCing time. "Deficit" is
   accumulated as `gc_time - runtime * runtime_weight`, and is compared against
   `threshold` to determine whether to take action. (default: 5)
 * `action` (default: 0): what action should be taken when `threshold` is
   exceeded. If zero, jvmquake attempts to produce an OOM within the JVM
   (allowing standard OOM handling such as `HeapDumpOnOutOfMemoryError` to
   trigger). If nonzero, jvmquake raises that signal number as an OS-level
   signal. **Regardless of the action, the JVM is then forcibly killed via a
   `SIGKILL`.**

## Algorithm Details
To achieve our goal, we build on `jvmkill`. In addition to dying when we see a
[`ResourceExhausted`](https://docs.oracle.com/javase/8/docs/platform/jvmti/jvmti.html#ResourceExhausted)
event, `jvmquake` keeps track of every GC entrance and exit that pause the
application using
[`GarbageCollectionStart`](https://docs.oracle.com/javase/8/docs/platform/jvmti/jvmti.html#GarbageCollectionStart)
and
[`GarbageCollectionFinish`](https://docs.oracle.com/javase/8/docs/platform/jvmti/jvmti.html#GarbageCollectionFinish).
`jvmquake` then keeps a *token bucket* algorithm to keep track of how
much time is spent GCing relative to running application code. Note that per
the jvmti spec these only track *stop the world* pausing phases of collections.
. The following pseudocode is essentially all of `jvmquake`:

```python3
# The bucket for keeping track of relative running and non running time
token_bucket : int = 0
# The amount of weight to give running seconds over GCing seconds. This defines
# our expected application throughput
runtime_weight : int = 5
# The amount of time that we must exceed the expected throughput by before
# triggering the signal and death actions
gc_threshold : int = 30

# Time bookeeping
last_gc_start : int = current_time()
last_gc_end : int = current_time()

def on_gc_start()
    last_gc_start = current_time()
    time_running = (last_gc_start - last_gc_end)
    token_bucket = max(0, token_bucket - (time_running * runtime_weight))

def on_gc_end()
    last_gc_end = current_time()
    time_gcing = (last_gc_end - last_gc_start)
    token_bucket += time_gcing

    if token_bucket > gc_threshold:
        take_action()
```

# Building and Usage
As `jvmquake` is a JVMTI c agent (so that it lives outside the heap and cannot
be affected by GC behavior), you must compile it before using it against
your JVM. You can either do this on the machine running the Java project or
externaly either in a debian package or as part of packaging the JVM itself.

```bash
# Compile jvmquake against the JVM the application is using. If you do not
# provide the path, the environment variable JAVA_HOME is used instead

make JAVA_HOME=/path/to/jvm
```

For example if the Oracle Java 8 JVM is located at `/usr/lib/jvm/java-8-oracle`:

```bash
make JAVA_HOME=/usr/lib/jvm/java-8-oracle
```

The agent is now available as `libjvmquake.so`.

## How to Use the Agent
Once you have the agent built, to use it just run your java program with
`agentpath` or `agentlib`.

```
java -agentpath:/path/to/libjvmquake.so <your java program here>
```

The default settings are 30 seconds of GC deficit with a 1:5 gc:running time
weight, and the default action is to trigger an in JVM OOM. These defaults
are reasonable for a latency critical java application.

If you want different settings you can pass options per the
[option specification](#knobs-and-options).

```
java -agentpath:/path/to/libjvmquake.so=<options> <your java program here>
```

Some examples:

If you want to cause a java level `OOM` when the program exceeds 30 seconds of
deficit where running time is equally weighted to gc time:
```
java -agentpath:/path/to/libjvmquake.so=30,1,0 <your java program here>
```

If you want to trigger an OS **core dump** and then die when the program
exceeds 30 seconds of deficit where running time is 5:1 weighted to gc time:
```
java -agentpath:/path/to/libjvmquake.so=30,1,6 <your java program here>
```

If you want to trigger a `SIGKILL` immediately without any form of diagnostics:
```
java -agentpath:/path/to/libjvmquake.so=30,1,9 <your java program here>
```

If you want to trigger a `SIGTERM` without any form of diagnostics:
```
java -agentpath:/path/to/libjvmquake.so=30,1,15 <your java program here>
```

If you want to cause a java level `OOM` when the program exceeds 60 seconds of
deficit where running time is 10:1 weighted to gc time:
```
java -agentpath:/path/to/libjvmquake.so=60,10,0 <your java program here>
```

# Testing
`jvmquake` comes with a test suite of OOM conditions (running out of memory,
threads, gcing too much, etc) which you can run if you have `tox` and
`python3` available:

```bash
# Run the test suite which uses tox, pytest, and plumbum under the hood
# to run jvmquake through numerous difficult failure modes
make test
```

If you have docker you can also run the tests with that
```bash
# Run the test suite via Docker
make docker
```

Coming soon: A test suite showing that the JVM options don't work.
