import os

from plumbum import local, BG


JAVA_HOME=os.environ.get('JAVA_HOME')
assert JAVA_HOME != None
java_cmd = local["{0}/bin/java".format(JAVA_HOME)]
agent_path = "-agentpath:{0}/libjvmquake.so".format(os.getcwd())
class_path = "{0}/tests".format(os.getcwd())


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

