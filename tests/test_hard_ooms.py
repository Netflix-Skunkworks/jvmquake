import os
import time

from pathlib import Path

from environment import agent_path
from environment import assert_files
from environment import CHECK_CORES
from environment import class_path
from environment import cleanup
from environment import core_ulimit
from environment import java_cmd


def test_jvmquake_cms_slow_death_oom():
    """
    Executes a program which over time does way more GC than actual execution
    We use the zero option to indicate to jvmquake to trigger a java level
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


def test_jvmquake_g1_slow_death_oom():
    """
    Executes a program which over time does way more GC than actual execution
    We use the zero option to indicate to jvmquake to trigger a java level
    OOM and cause a heap dump.
    """

    g1_slow_death = java_cmd[
        '-Xmx100m',
        '-XX:+HeapDumpOnOutOfMemoryError',
        '-XX:+UseG1GC',
        '-XX:+PrintGCDetails',
        '-XX:+PrintGCDateStamps',
        '-XX:+PrintGCApplicationConcurrentTime',
        '-XX:+PrintGCApplicationStoppedTime',
        '-Xloggc:gclog',
        agent_path + "=1,1,0",
        '-cp', class_path,
        'SlowDeathOOM'
    ]
    print("Executing Complex G1GC Slow Death OOM")
    print("[{0}]".format(g1_slow_death))
    with g1_slow_death.bgrun(retcode=-9, timeout=10) as proc:
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


def test_jvmquake_cms_touch_warning():
    """
    Executes a program which over time does way more GC than actual execution
    Then test that jvmquake correctly touches the correct file
    """
    jvmquake_warn_path = Path('/tmp/jvmquake_warn_gc')
    files = [jvmquake_warn_path]
    cleanup(*files)

    start_time = time.time()

    cms_slow_death_warn_only = java_cmd[
        '-Xmx100m',
        '-XX:+UseParNewGC',
        '-XX:+UseConcMarkSweepGC',
        '-XX:CMSInitiatingOccupancyFraction=75',
        agent_path + "=3,1,9,warn=1",
        '-cp', class_path,
        'SlowDeathOOM'
    ]

    print("Executing Complex CMS Slow Death OOM")
    print("[{0}]".format(cms_slow_death_warn_only))
    with cms_slow_death_warn_only.bgrun(retcode=-9, timeout=10) as proc:
        pid = proc.pid

    print("Ran pid {}".format(pid))
    try:
        assert_files(*files)
        mtime = os.path.getmtime(str(jvmquake_warn_path))
        assert mtime > (start_time + 1)
    finally:
        cleanup(*files)


def test_jvmquake_cms_touch_warning_custom_path():
    """
    Executes a program which over time does way more GC than actual execution
    Then test that jvmquake correctly touches the correct file
    """
    jvmquake_warn_path = Path('/tmp/jvmquake_custom_path')
    files = [jvmquake_warn_path]
    cleanup(*files)

    start_time = time.time()

    cms_slow_death_warn_only = java_cmd[
        '-Xmx100m',
        '-XX:+UseParNewGC',
        '-XX:+UseConcMarkSweepGC',
        '-XX:CMSInitiatingOccupancyFraction=75',
        agent_path + "=5,1,9,warn=2,touch=" + str(jvmquake_warn_path),
        '-cp', class_path,
        'SlowDeathOOM'
    ]

    print("Executing Complex CMS Slow Death OOM")
    print("[{0}]".format(cms_slow_death_warn_only))
    with cms_slow_death_warn_only.bgrun(retcode=-9, timeout=20) as proc:
        pid = proc.pid

    print("Ran pid {}".format(pid))
    try:
        assert_files(*files)
        mtime = os.path.getmtime(str(jvmquake_warn_path))
        assert mtime > (start_time + 2)
    finally:
        cleanup(*files)
