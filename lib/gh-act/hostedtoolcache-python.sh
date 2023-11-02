#!/bin/bash
# Ensure that the specified python exists in the github "hostedtoolcache"
set -euo pipefail
HERE="$(cd "$(dirname "$0")"; pwd)"
python_version="$1"

set -x
"$HERE"/hostedtoolcache.sh "$(pyenv prefix "$python_version")" Python "$@"

# needed?
#"$dst"/bin/python -m pip install --upgrade pip
