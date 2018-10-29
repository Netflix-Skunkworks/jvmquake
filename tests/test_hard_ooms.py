from pathlib import Path

from environment import *


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

    files = [gclog_path]
    # So ... core files are apparently super annoying to reliably generate
    # in Docker (or really on any system you don't control the value of
    # /proc/sys/kernel/core_pattern ) So we don't check it by default
    # set the CHECK_CORES env variable to test this too
    if CHECK_CORES:
        files.append(core_path)

    try:
        assert_files(*files)
        assert not heapdump_path.is_file()
    finally:
        cleanup(*files)
