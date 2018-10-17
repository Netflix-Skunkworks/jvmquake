import os
from pathlib import Path
import resource

from plumbum import local, BG
import pytest


java_home=os.environ.get('JAVA_HOME')
java_cmd = local["{0}/bin/java".format(java_home)]
agent_path = "-agentpath:{0}/libjvmquake.so".format(os.getcwd())
class_path = "{0}/tests".format(os.getcwd())


@pytest.fixture(scope='module')
def core_ulimit():
    import resource
    (x, y) = resource.getrlimit(resource.RLIMIT_CORE)
    resource.setrlimit(
        resource.RLIMIT_CORE,
        (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
    )
    yield
    resource.setrlimit(resource.RLIMIT_CORE, (x, y))


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


def assert_files(*paths):
    for path in paths:
        assert path.is_file()


def cleanup(*paths):
    [path.unlink() for path in paths if path.is_file()]


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

    files = (heapdump_path, core_path)
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
    assert "unable to create new native thread" in stderr
