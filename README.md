[![Build Status](https://travis-ci.org/jolynch/jvmquake.svg?branch=master)](https://travis-ci.org/jolynch/jvmquake)

# `jvmquake`
A JVMTI agent that attaches to your JVM and automatically signals and kills it
when the program has become unstable.

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
* Documentation (almost done)
* Error handling (next)

# Motivation
Java Applications, especially databases such as Elasticsearch and Cassandra
frequently enter GC spirals of death, either resulting in OOM or Concurrent
mode failures (aka "CMF" per CMS parlance although G1 has similar issues with
frequent mixed mode collections). Concurrent mode failures, when the old gen
collector is running frequently expending a lot of CPU resources but is still
able to reclaim enough memory so that the application does not cause a full
OOM, are particularly pernicious as they appear as 10-30s "partitions" (shorter
if your heap is smaller, longer if thye heap is larger) and then heal, and then
partition, and then heal, etc ... This repeated partitioning causes great
confusion for distributed JVM based applications and especially databases.  The
JVM has various flags to try to address these issues:

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

# Building
```bash
# Ensure that JAVA_HOME is pointing to the JVM you want to build for and run

make

# Or you can run make with the JAVA_HOME specified manually

make JAVA_HOME=/path/to/jvm

# Now the agent is available at libjvmquake.so
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

Coming soon: A test suite showing that the JVM options don't work.

# Using
Once you've got the agent built, to use it just run your java program
with `agentpath` or `agentlib`.

```
java -agentpath:/path/to/libjvmquake.so=<options> <your java program here>
```

Options should conform to the [option specification](#knobs-and-options). The
defaults are a 30 second GC deficit must accumulate with a 1:5 gc:running time
weight (so we must GC 5 times as much as we run before we accumulate GC
deficit).

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
