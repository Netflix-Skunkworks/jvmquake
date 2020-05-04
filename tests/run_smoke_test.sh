#!/bin/bash
# We want to run a single mininal smoketest of jvmquake installed to the
# system (via e.g. a deb) that doesn't run through all the cases but
# doesn't depend on any external packages that might hide dependency issues
set -euf -o pipefail
set -x

if [ -d "/work/dist/" ]; then
    DEB=$(find /work/dist -name 'jvmquake*.deb')
    dpkg -i ${DEB}
fi

JAVA=${JAVA_HOME}/bin/java
function cleanup() {
    rm -f java_stderr
    bash -c 'rm -f *.hprof'
    rm -f core
}

trap cleanup EXIT

echo "#########################"
echo "# Excessive GC CMS test #"
echo "#########################"

$JAVA -Xmx100m -XX:+UseConcMarkSweepGC -XX:CMSInitiatingOccupancyFraction=75 -XX:+HeapDumpOnOutOfMemoryError -agentpath:libjvmquake.so=1,1,0 -cp $(pwd)/tests SlowDeathOOM 2> java_stderr &
JAVA_PID=$!

wait

# We should have a heap dump file
test -f java_pid${JAVA_PID}.hprof

# Signs that jvmquake did its thing
# note that due to the set -euf above if any of these fail the script fails
grep "Excessive GC" java_stderr
grep "Requested array size exceeds VM limit" java_stderr

cleanup

echo "##########################"
echo "# Excessive GC G1GC test #"
echo "##########################"

$JAVA -Xmx100m -XX:+UseG1GC -XX:+HeapDumpOnOutOfMemoryError -agentpath:libjvmquake.so=1,1,0 -cp $(pwd)/tests SlowDeathOOM 2> java_stderr &
JAVA_PID=$!

wait

# We should have a heap dump file
test -f java_pid${JAVA_PID}.hprof

# Signs that jvmquake did its thing
# note that due to the set -euf above if any of these fail the script fails
grep "Excessive GC" java_stderr
grep "Requested array size exceeds VM limit" java_stderr

cleanup
