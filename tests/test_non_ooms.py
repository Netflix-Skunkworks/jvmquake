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
