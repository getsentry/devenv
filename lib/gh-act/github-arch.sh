#!/bin/bash
# Get the machine architecture name, using the github spelling.
set -euo pipefail
arch=${1:-$(uname -m)}

case "$arch" in
  x64|amd64|x86_64) echo x64;;
  arm64|aarch64) echo arm64;;
  x86) echo x86;;
  *)
    echo >&2 "unrecognized arch: '$arch'"
    exit 1
  ;;
esac
