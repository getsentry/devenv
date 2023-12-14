#!/usr/bin/env bash
set -euxo pipefail

# macos/bsd sed
/usr/bin/sed -i "s/^version =.*/version = \"$2\"/" pyproject.toml
