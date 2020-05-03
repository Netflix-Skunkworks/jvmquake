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

import os
import glob
from pathlib import Path

from plumbum import local
import pytest


CHECK_CORES = os.environ.get('CHECK_CORES', '') != ''
JAVA_HOME = os.environ.get('JAVA_HOME')
assert JAVA_HOME is not None

AGENT_DIR = os.environ.get('AGENT_DIR', Path(os.getcwd(), 'build').as_posix())
AGENT_PATH = glob.glob('{}/*.so'.format(AGENT_DIR))
if len(AGENT_PATH) == 0:
    # assume that jvmquake has been installed
    AGENT_PATH='libjvmquake.so'
else:
    AGENT_PATH=AGENT_PATH[0]

java_cmd = local["{0}/bin/java".format(JAVA_HOME)]
agent_path = "-agentpath:{0}".format(AGENT_PATH)
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
