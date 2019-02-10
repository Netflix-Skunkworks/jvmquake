from environment import agent_path
from environment import class_path
from environment import java_cmd


def test_jvmquake_healthy_jvm():
    """
    Executes a program which should work and exit after 10 seconds
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
