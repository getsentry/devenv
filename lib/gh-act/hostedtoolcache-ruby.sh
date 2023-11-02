#!/bin/bash
# Ensure that the specified python exists in the github "hostedtoolcache"
set -euo pipefail
HERE="$(cd "$(dirname "$0")"; pwd)"
ruby_version="$1"

set -x
"$HERE"/hostedtoolcache.sh "$(rbenv prefix "$ruby_version")" Ruby "$@"
