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


def assert_files(*paths):
    for path in paths:
        assert path.is_file()


def cleanup(*paths):
    [path.unlink() for path in paths if path.is_file()]


def test_jvmquake_cms_slow_death_oom():
    """
    Executes a program which over time does way more GC than actual execution
    We use the zero option to indicate to jvmkill to trigger a java level
    OOM and cause a heap dump.
    """

    cms_slow_death = java_cmd[
        '-Xmx100m',
        '-XX:+HeapDumpOnOutOfMemoryError',
        '-XX:+UseParNewGC',
        '-XX:+UseConcMarkSweepGC',
        '-XX:CMSInitiatingOccupancyFraction=75',
        '-XX:+PrintGCDetails',
        '-XX:+PrintGCDateStamps',
        '-XX:+PrintGCApplicationConcurrentTime',
        '-XX:+PrintGCApplicationStoppedTime',
        '-Xloggc:gclog',
        agent_path + "=1,1,0",
        '-cp', class_path,
        'SlowDeathOOM'
    ]
    print("Executing Complex CMS Slow Death OOM")
    print("[{0}]".format(cms_slow_death))
    with cms_slow_death.bgrun(retcode=-9, timeout=10) as proc:
        pid = proc.pid

    heapdump_path = Path.cwd().joinpath("java_pid{0}.hprof".format(pid))
    gclog_path = Path.cwd().joinpath('gclog')

    files = (heapdump_path, gclog_path)
    try:
        assert_files(*files)
    finally:
        cleanup(*files)


def test_jvmquake_cms_slow_death_core(core_ulimit):
    """
    Executes a program which over time does way more GC than actual execution
    """
    cms_slow_death = java_cmd[
        '-Xmx100m',
        '-XX:+HeapDumpOnOutOfMemoryError',
        '-XX:+UseParNewGC',
        '-XX:+UseConcMarkSweepGC',
        '-XX:CMSInitiatingOccupancyFraction=75',
        '-XX:+PrintGCDetails',
        '-XX:+PrintGCDateStamps',
        '-XX:+PrintGCApplicationConcurrentTime',
        '-XX:+PrintGCApplicationStoppedTime',
        '-Xloggc:gclog',
        agent_path + "=1,1,6",
        '-cp', class_path,
        'SlowDeathOOM'
    ]
    print("Executing Complex CMS Slow Death OOM")
    print("[{0}]".format(cms_slow_death))
    with cms_slow_death.bgrun(retcode=-6, timeout=10) as proc:
        pid = proc.pid

    heapdump_path = Path.cwd().joinpath("java_pid{0}.hprof".format(pid))
    gclog_path = Path.cwd().joinpath('gclog')
    core_path = Path.cwd().joinpath('core')

    files = (gclog_path, core_path)
    try:
        assert_files(*files)
        assert not heapdump_path.is_file()
    finally:
        cleanup(*files)
