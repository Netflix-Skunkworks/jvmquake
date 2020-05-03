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

import re
import pytest
from pathlib import Path

from environment import agent_path
from environment import assert_files
from environment import CHECK_CORES
from environment import class_path
from environment import cleanup
from environment import core_ulimit
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


def test_jvmquake_normal_oom():
    """
    Executes a program which runs out of memory through native allocations
    """
    easy_oom = java_cmd[
        '-Xmx10m',
        '-XX:+HeapDumpOnOutOfMemoryError',
        "-XX:OnOutOfMemoryError=/bin/touch OnOutOfMemoryError_%p.ran",
        agent_path,
        '-cp', class_path,
        'EasyOOM'
    ]
    print("Executing simple OOM")
    print("[{0}]".format(easy_oom))
    with easy_oom.bgrun(retcode=-9, timeout=10) as proc:
        pid = proc.pid

    heapdump_path = Path.cwd().joinpath("java_pid{0}.hprof".format(pid))
    ooome_path = Path.cwd().joinpath("OnOutOfMemoryError_{0}.ran".format(pid))

    files = (heapdump_path, ooome_path)
    try:
        assert_files(*files)
    finally:
        cleanup(*files)


def test_jvmquake_coredump_oom(core_ulimit):
    """
    Executes a program which runs out of memory through native allocations
    """
    easy_oom = java_cmd[
        '-Xmx10m',
        '-XX:+HeapDumpOnOutOfMemoryError',
        agent_path + "=10,1,6",
        '-cp', class_path,
        'EasyOOM'
    ]
    print("Executing simple OOM causing core dump")
    print("[{0}]".format(easy_oom))
    with easy_oom.bgrun(retcode=-6, timeout=10) as proc:
        pid = proc.pid

    heapdump_path = Path.cwd().joinpath("java_pid{0}.hprof".format(pid))
    core_path = Path.cwd().joinpath("core")

    files = [heapdump_path]
    # So ... core files are apparently super annoying to reliably generate
    # in Docker (or really on any system you don't control the value of
    # /proc/sys/kernel/core_pattern ) So we don't check it by default
    # set the CHECK_CORES env variable to test this too
    if CHECK_CORES:
        files.append(core_path)

    try:
        assert_files(*files)
    finally:
        cleanup(*files)


def test_jvmquake_forced_oom(core_ulimit):
    """
    Executes a program which runs out of memory through native allocations
    and ensures that we properly parse the "0" option
    """
    easy_oom = java_cmd[
        '-Xmx10m',
        '-XX:+HeapDumpOnOutOfMemoryError',
        agent_path + "=10,1,0",
        '-cp', class_path,
        'EasyOOM'
    ]
    print("Executing simple OOM causing core dump")
    print("[{0}]".format(easy_oom))
    with easy_oom.bgrun(retcode=-9, timeout=10) as proc:
        pid = proc.pid

    heapdump_path = Path.cwd().joinpath("java_pid{0}.hprof".format(pid))

    files = [heapdump_path]

    try:
        assert_files(*files)
    finally:
        cleanup(*files)


def test_jvmquake_thread_oom(thread_ulimit):
    """
    Executes a program which runs out of memory through lots of Thread
    allocations
    """
    thread_oom = java_cmd[
        '-Xmx100m',
        '-XX:+HeapDumpOnOutOfMemoryError',
        agent_path,
        '-cp', class_path,
        'EasyThreadOOM'
    ]
    print("Executing thread OOM")
    print("[{0}]".format(thread_oom))
    (_, stdout, stderr) = thread_oom.run(retcode=-9, timeout=10)
    # Java 11 took out the word "new"
    assert "unable to create" in stderr
    assert "native thread" in stderr
