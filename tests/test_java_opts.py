# Copyright 2019 Netflix, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path

import plumbum
import pytest

from environment import JAVA_MAJOR_VERSION
from environment import assert_files
from environment import class_path
from environment import cleanup
from environment import java_cmd


@pytest.fixture()
def thread_ulimit():
    import resource
    (x, y) = resource.getrlimit(resource.RLIMIT_NPROC)
    resource.setrlimit(
        resource.RLIMIT_NPROC,
        (x - 1000, y)
    )
    yield
    resource.setrlimit(resource.RLIMIT_NPROC, (x, y))


def test_jvm_normal_oom():
    """
    Executes a program which runs out of memory through native allocations
    ExitOnOutOfMemoryError should work here
    """
    easy_oom = java_cmd[
        '-Xmx10m',
        '-XX:+HeapDumpOnOutOfMemoryError',
        "-XX:OnOutOfMemoryError=/bin/touch OnOutOfMemoryError_%p.ran",
        "-XX:+ExitOnOutOfMemoryError",
        '-cp', class_path,
        'EasyOOM'
    ]
    print("Executing simple OOM")
    print("[{0}]".format(easy_oom))
    with easy_oom.bgrun(retcode=3, timeout=10) as proc:
        pid = proc.pid

    heapdump_path = Path.cwd().joinpath("java_pid{0}.hprof".format(pid))
    ooome_path = Path.cwd().joinpath("OnOutOfMemoryError_{0}.ran".format(pid))

    files = (heapdump_path, ooome_path)
    try:
        assert_files(*files)
    finally:
        cleanup(*files)


def test_jvm_exit_oom(thread_ulimit):
    """
    Runs the JVM out of threads.
    ExitOnOutOfMemoryError does not work for these thread leaks.
    """
    thread_oom = java_cmd[
        '-Xmx100m',
        '-XX:+ExitOnOutOfMemoryError',
        '-cp', class_path,
        'EasyThreadOOM'
    ]
    print("Executing thread OOM")
    print("[{0}]".format(thread_oom))
    with (pytest.raises(plumbum.commands.processes.ProcessTimedOut)):
        thread_oom.run(retcode=3, timeout=10)


def test_jvm_cms_slow_death_oom():
    """
    Executes a program which over time does way more GC than actual execution

    In this case -XX:GCTimeLimit and -XX:GCHeapFreeLimit do squat
    """

    if JAVA_MAJOR_VERSION > 8:
        cms_slow_death = java_cmd[
            '-Xmx100m',
            '-XX:+UseConcMarkSweepGC',
            '-XX:CMSInitiatingOccupancyFraction=75',
            '-XX:GCTimeLimit=20',
            '-XX:GCHeapFreeLimit=80',
            '-cp', class_path,
            'SlowDeathOOM'
        ]
    else:
        cms_slow_death = java_cmd[
            '-Xmx100m',
            '-XX:+UseParNewGC',
            '-XX:+UseConcMarkSweepGC',
            '-XX:CMSInitiatingOccupancyFraction=75',
            '-XX:GCTimeLimit=20',
            '-XX:GCHeapFreeLimit=80',
            '-cp', class_path,
            'SlowDeathOOM'
        ]
    print("Executing Complex CMS Slow Death OOM")
    print("[{0}]".format(cms_slow_death))
    with (pytest.raises(plumbum.commands.processes.ProcessTimedOut)):
        cms_slow_death.run(retcode=3, timeout=10)


def test_jvm_g1_slow_death_oom():
    """
    Executes a program which over time does way more GC than actual execution

    In this case -XX:GCTimeLimit and -XX:GCHeapFreeLimit do squat for G1GC
    """
    g1_slow_death = java_cmd[
        '-Xmx100m',
        '-XX:+UseG1GC',
        '-XX:GCTimeLimit=20',
        '-XX:GCHeapFreeLimit=80',
        '-cp', class_path,
        'SlowDeathOOM'
    ]
    print("Executing Complex G1 Slow Death OOM")
    print("[{0}]".format(g1_slow_death))
    with (pytest.raises(plumbum.commands.processes.ProcessTimedOut)):
        g1_slow_death.run(retcode=3, timeout=10)
