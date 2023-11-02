#!/bin/bash
# Ensure that the specified python exists in the github "hostedtoolcache"
set -euo pipefail
src="$1"
github_tool="$2"
tool_version="$3"
github_arch="$4"
dst="/opt/hostedtoolcache/$github_tool/$tool_version/$github_arch"

set -x
mkdir -p "$(dirname "$dst")"
ln -sfT "$src" "$dst"
touch "$dst.complete"  # actions/setup-python keys on this file's existence

ls -l "$dst/bin"
