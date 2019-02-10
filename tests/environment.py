import os

from plumbum import local
import pytest


CHECK_CORES = os.environ.get('CHECK_CORES', '') != ''
JAVA_HOME = os.environ.get('JAVA_HOME')
assert JAVA_HOME is not None

java_cmd = local["{0}/bin/java".format(JAVA_HOME)]
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
