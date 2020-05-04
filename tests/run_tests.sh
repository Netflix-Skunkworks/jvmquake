#!/bin/bash

set -euf -o pipefail

if [ -d "/work/dist/" ]; then
    DEB=$(find /work/dist -name 'jvmquake*.deb')
    dpkg -i ${DEB}
fi

tox -e test
tox -e test_jvm
