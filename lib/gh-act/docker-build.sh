#!/bin/bash
set -euo pipefail

github_arch="$(./github-arch.sh)"
python_version="$(
  ./github-python-versions.sh "$github_arch" |
    grep -m1 -E '^3.11\b'
)"
tag="localhost/devenv-gh-act:python$(
  sed '
    s/\.[^.]*$//  # delete the patch number
    s/\.//g  # remove any remaining dots
  ' \
  <<< "$python_version"
)"

set -x
docker buildx build \
  --progress=plain \
  --tag="$tag" \
  --load \
  --build-arg="PYTHON_VERSION=$python_version" \
  --build-arg="GITHUB_ARCH=$github_arch" \
  .

: Sucessfully built "$tag"
