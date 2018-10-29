import os

from environment import *


def test_jvmquake_healthy_jvm():
    """
    Executes a program which should work and exit after 20 seconds
    """
    easy_oom = java_cmd[
        '-Xmx10m',
        agent_path,
        '-cp', class_path,
        'EasyNonOOM'
    ]
    print("Executing NON-OOM program")
    print("[{0}]".format(easy_oom))
    easy_oom.run(retcode=0, timeout=15)

