#!/bin/bash
# Ensure that the specified python exists in the github "hostedtoolcache"
set -euo pipefail
github_arch="$1"
python_version="$2"
dst="/opt/hostedtoolcache/Python/$python_version/$github_arch"

set -x
src="$(pyenv prefix "$python_version")"
mkdir -p "$(dirname "$dst")"
ln -sfT "$src" "$dst"
touch "$dst.complete"  # actions/setup-python keys on this file's existence

ls -l "$dst/bin"
"$dst"/bin/python -m pip install --upgrade pip
