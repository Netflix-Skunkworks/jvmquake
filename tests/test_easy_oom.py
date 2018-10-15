import os
from pathlib import Path

from plumbum import local, BG


java_home=os.environ.get('JAVA_HOME')
java_cmd = local["{0}/bin/java".format(java_home)]
agent_path = "-agentpath:{0}/libjvmquake.so".format(os.getcwd())
class_path = "{0}/tests".format(os.getcwd())


def cleanup(*paths):
    [path.unlink() for path in paths if path.is_file()]


def test_jvmquake_easy():
    easy_oom = java_cmd[
        '-Xmx1m',
        '-XX:+HeapDumpOnOutOfMemoryError',
        "-XX:OnOutOfMemoryError=/bin/touch OnOutOfMemoryError_%p.ran",
        agent_path,
        '-cp', class_path,
        'EasyOOM'
    ]
    with easy_oom.bgrun(retcode=-9, timeout=10) as proc:
        pid = proc.pid

    heapdump_path = Path.cwd().joinpath("java_pid{0}.hprof".format(pid))
    ooome = Path.cwd().joinpath("OnOutOfMemoryError_{0}.ran".format(pid))

    try:
        assert heapdump_path.is_file()
        assert ooome.is_file()
    finally:
        cleanup(heapdump_path, ooome)
